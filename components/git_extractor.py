import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import git

from langflow.custom.custom_component.component import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.data import Data
from langflow.schema.message import Message


class GitExtractorComponent(Component):
    display_name = "Git File Extractor"
    description = "Extracts a specific file from a Git repository with detailed information"
    icon = "GitLoader"

    inputs = [
        MessageTextInput(
            name="repository_url",
            display_name="Repository URL",
            info="URL of the Git repository. Accepts GitHub web URLs (https://github.com/user/repo) or direct Git URLs (https://github.com/user/repo.git)",
            value="",
        ),
        MessageTextInput(
            name="file_path",
            display_name="File Path",
            info="Path to the specific file in the repository (e.g., src/main.py, README.md)",
            value="",
        ),
    ]

    outputs = [
        Output(
            display_name="File Content",
            name="file_content",
            method="get_file_content",
        ),
        Output(
            display_name="File Information", 
            name="file_info", 
            method="get_file_info"
        ),
        Output(
            display_name="File History", 
            name="file_history", 
            method="get_file_history"
        ),
        Output(
            display_name="Repository Info", 
            name="repository_info", 
            method="get_repository_info"
        ),
    ]

    def normalize_github_url(self, url: str) -> str:
        """Convert GitHub web URLs to proper Git repository URLs."""
        if not url:
            return url
            
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Convert GitHub web URLs to Git URLs
        if 'github.com' in url:
            # Remove /blob/branch/ or /tree/branch/ parts
            if '/blob/' in url:
                url = url.split('/blob/')[0]
            elif '/tree/' in url:
                url = url.split('/tree/')[0]
            
            # Ensure it ends with .git for better compatibility
            if not url.endswith('.git'):
                url += '.git'
        
        return url

    @asynccontextmanager
    async def temp_git_repo(self):
        """Async context manager for temporary git repository cloning."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Normalize the URL before cloning
            normalized_url = self.normalize_github_url(self.repository_url)
            self.status = f"Cloning repository from: {normalized_url}"
            
            # Clone is still sync but wrapped in try/finally
            git.Repo.clone_from(normalized_url, temp_dir)
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def get_file_content(self) -> Message:
        """Extract content of the specific file."""
        try:
            if not self.repository_url:
                error_message = "Error: Repository URL is required"
                self.status = error_message
                return Message(text=error_message)
                
            if not self.file_path:
                error_message = "Error: File path is required"
                self.status = error_message
                return Message(text=error_message)
                
            async with self.temp_git_repo() as temp_dir:
                file_full_path = Path(temp_dir) / self.file_path
                
                if not file_full_path.exists():
                    error_message = f"Error: File '{self.file_path}' not found in repository"
                    self.status = error_message
                    return Message(text=error_message)
                
                try:
                    async with aiofiles.open(file_full_path, encoding="utf-8") as f:
                        file_content = await f.read()
                except UnicodeDecodeError:
                    file_content = "[BINARY FILE - Cannot display content]"
                
                self.status = f"Successfully extracted file: {self.file_path}"
                return Message(text=file_content)
                
        except git.GitError as e:
            error_message = f"Error extracting file content: {e!s}"
            self.status = error_message
            return Message(text=error_message)

    async def get_file_info(self) -> list[Data]:
        """Get detailed information about the specific file."""
        try:
            if not self.repository_url:
                error_result = [Data(data={"error": "Repository URL is required"})]
                self.status = error_result
                return error_result
                
            if not self.file_path:
                error_result = [Data(data={"error": "File path is required"})]
                self.status = error_result
                return error_result
                
            async with self.temp_git_repo() as temp_dir:
                file_full_path = Path(temp_dir) / self.file_path
                
                if not file_full_path.exists():
                    error_result = [Data(data={"error": f"File '{self.file_path}' not found in repository"})]
                    self.status = error_result
                    return error_result
                
                # Get file stats
                stat = file_full_path.stat()
                
                # Determine if file is binary
                is_binary = False
                encoding = "utf-8"
                try:
                    async with aiofiles.open(file_full_path, encoding="utf-8") as f:
                        content = await f.read()
                        line_count = content.count('\n') + 1 if content else 0
                        char_count = len(content)
                        word_count = len(content.split()) if content else 0
                except UnicodeDecodeError:
                    is_binary = True
                    line_count = 0
                    char_count = 0
                    word_count = 0
                    encoding = "binary"
                
                file_info = {
                    "path": self.file_path,
                    "name": file_full_path.name,
                    "extension": file_full_path.suffix,
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "is_binary": is_binary,
                    "encoding": encoding,
                    "line_count": line_count,
                    "character_count": char_count,
                    "word_count": word_count,
                    "modified_time": str(stat.st_mtime),
                }
                
                result = [Data(data=file_info)]
                self.status = result
                return result
                
        except git.GitError as e:
            error_result = [Data(data={"error": f"Error getting file info: {e!s}"})]
            self.status = error_result
            return error_result

    async def get_file_history(self) -> list[Data]:
        """Get commit history for the specific file."""
        try:
            if not self.repository_url:
                error_result = [Data(data={"error": "Repository URL is required"})]
                self.status = error_result
                return error_result
                
            if not self.file_path:
                error_result = [Data(data={"error": "File path is required"})]
                self.status = error_result
                return error_result
                
            async with self.temp_git_repo() as temp_dir:
                repo = git.Repo(temp_dir)
                file_full_path = Path(temp_dir) / self.file_path
                
                if not file_full_path.exists():
                    error_result = [Data(data={"error": f"File '{self.file_path}' not found in repository"})]
                    self.status = error_result
                    return error_result
                
                # Get commit history for the file
                commits = list(repo.iter_commits(paths=self.file_path, max_count=10))
                
                commit_history = []
                for commit in commits:
                    commit_data = {
                        "hash": commit.hexsha,
                        "short_hash": commit.hexsha[:7],
                        "author": str(commit.author),
                        "email": commit.author.email,
                        "message": commit.message.strip(),
                        "date": str(commit.committed_datetime),
                        "timestamp": commit.committed_date,
                    }
                    commit_history.append(commit_data)
                
                result = [Data(data={
                    "file_path": self.file_path,
                    "total_commits": len(commit_history),
                    "commits": commit_history
                })]
                self.status = result
                return result
                
        except git.GitError as e:
            error_result = [Data(data={"error": f"Error getting file history: {e!s}"})]
            self.status = error_result
            return error_result

    async def get_repository_info(self) -> list[Data]:
        """Get basic repository information."""
        try:
            if not self.repository_url:
                error_result = [Data(data={"error": "Repository URL is required"})]
                self.status = error_result
                return error_result
                
            async with self.temp_git_repo() as temp_dir:
                repo = git.Repo(temp_dir)
                repo_info = {
                    "repository_name": self.repository_url.split("/")[-1],
                    "repository_url": self.repository_url,
                    "default_branch": repo.active_branch.name,
                    "target_file": self.file_path,
                    "remote_urls": [remote.url for remote in repo.remotes],
                    "last_commit": {
                        "hash": repo.head.commit.hexsha,
                        "author": str(repo.head.commit.author),
                        "message": repo.head.commit.message.strip(),
                        "date": str(repo.head.commit.committed_datetime),
                    },
                    "total_branches": len(list(repo.branches)),
                    "file_exists": (Path(temp_dir) / self.file_path).exists() if self.file_path else False,
                }
                result = [Data(data=repo_info)]
                self.status = result
                return result
        except git.GitError as e:
            error_result = [Data(data={"error": f"Error getting repository info: {e!s}"})]
            self.status = error_result
            return error_result
