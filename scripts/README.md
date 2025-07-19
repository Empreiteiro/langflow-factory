# Langflow Flows Backup & Import

Python scripts to backup and import flows from your Langflow installation.

## Features

### Backup Script (`backup_flows_zip.py`)
- ✅ Downloads all flows from Langflow installation via API
- ✅ Saves each flow in separate JSON file with metadata
- ✅ Sends automatically to GitHub repository
- ✅ GitHub token authentication support
- ✅ Detailed process logs

### Import Script (`import_flows.py`)
- ✅ Import individual flow JSON files to Langflow
- ✅ Import multiple flows from a directory
- ✅ Support for project-specific imports
- ✅ List available projects
- ✅ Environment variable configuration
- ✅ Detailed error handling and logging

### Projects List Script (`list_projects.py`)
- ✅ List all Langflow projects with details
- ✅ Show project IDs, names, and descriptions
- ✅ Export projects list to JSON file
- ✅ Environment variable configuration
- ✅ Detailed and summary view options

### Flows List Script (`list_flows.py`)
- ✅ List all Langflow flows with pagination support
- ✅ Show flow IDs, names, descriptions, and status
- ✅ Filter flows (remove examples, components only, header flows)
- ✅ Get details for specific flow by ID
- ✅ Export flows list to JSON file
- ✅ Environment variable configuration
- ✅ Detailed and summary view options

### Components List Script (`list_components.py`)
- ✅ List all Langflow components with pagination support
- ✅ Show component IDs, names, types, and descriptions
- ✅ Filter components (remove examples, header flows)
- ✅ Get details for specific component by ID
- ✅ Export components list to JSON file
- ✅ Environment variable configuration
- ✅ Detailed and summary view options

### Components Download Script (`download_components.py`)
- ✅ Download all Langflow components as individual JSON files
- ✅ Save components to local directory with organized filenames
- ✅ Create components index file with metadata
- ✅ Filter components (remove examples, header flows)
- ✅ Download specific component by ID
- ✅ Environment variable configuration
- ✅ Safe filename sanitization

### File Upload Script (`upload_file.py`)
- ✅ Upload any file type to Langflow using v2 API
- ✅ Automatic MIME type detection
- ✅ Environment variable configuration
- ✅ Command line argument support
- ✅ Detailed upload information and file paths
- ✅ Error handling and validation

### Files List Script (`list_files.py`)
- ✅ List all files from Langflow using v2 API
- ✅ Show file IDs, names, paths, and metadata
- ✅ Export files list to JSON file
- ✅ Environment variable configuration
- ✅ Command line argument support
- ✅ Detailed file information and usage examples

### Upload and Run Script (`upload_and_run.py`)
- ✅ Upload any file type to Langflow using v2 API
- ✅ Run Langflow flow with uploaded file
- ✅ Automatic MIME type detection
- ✅ Environment variable configuration
- ✅ Command line argument support
- ✅ Customizable flow parameters (flow_id, course_id, user_id, input_value)

### Project Transfer Script (`transfer_project.py`)
- ✅ Transfer specific project between Langflow installations
- ✅ Download all flows from source project
- ✅ Upload flows to target project
- ✅ Verify project existence in source and target
- ✅ Environment variable configuration for source and target
- ✅ Detailed transfer progress and summary
- ✅ Error handling and rollback support

## Installation

1. Clone this repository or download the files
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure the `.env` file:

```bash
# Option 1: Use the automatic script
python setup_env.py

# Option 2: Configure manually
cp env.example .env
# Edit the .env file with your settings
```

4. Verify and test the configuration:

```bash
# Check configurations
python check_env.py

# Test Langflow connection
python test_connection.py
```

## Usage

### Basic Backup (save locally only)

```bash
# With .env file configured
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py --langflow-url http://localhost:3000
```

### Backup with GitHub upload

```bash
# With .env file configured
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-langflow-token \
    --github-repo your-username/your-repo \
    --github-token your-github-token \
    --push-to-github
```

### Available Parameters

#### Backup Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ✅ | URL of your Langflow installation |
| `--langflow-token` | ❌ | Langflow authentication token (x-api-key) |
| `--github-repo` | ❌ | GitHub repository (format: owner/repo) |
| `--github-token` | ❌ | GitHub access token |
| `--output-dir` | ❌ | Output directory (default: ./langflow_backup) |
| `--push-to-github` | ❌ | Flag to automatically send to GitHub |

#### Import Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--flow-file` | ❌ | Path to the JSON flow file to import |
| `--flow-directory` | ❌ | Directory containing JSON flow files to import |
| `--project-id` | ❌ | Target project ID for the flow (optional) |
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--list-projects` | ❌ | List available projects and exit |

#### Projects List Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--show-details` | ❌ | Show detailed project information |
| `--export-json` | ❌ | Export projects list to JSON file |
| `--output-file` | ❌ | Output file name for JSON export (default: projects_list.json) |

#### Flows List Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--show-details` | ❌ | Show detailed flow information |
| `--export-json` | ❌ | Export flows list to JSON file |
| `--output-file` | ❌ | Output file name for JSON export (default: flows_list.json) |
| `--page-size` | ❌ | Number of flows per page (default: 50) |
| `--include-example-flows` | ❌ | Include example flows in results (default: exclude) |
| `--components-only` | ❌ | Return only flow components |
| `--header-flows` | ❌ | Include header flows |
| `--flow-id` | ❌ | Get details for a specific flow ID |

#### Components List Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--show-details` | ❌ | Show detailed component information |
| `--export-json` | ❌ | Export components list to JSON file |
| `--output-file` | ❌ | Output file name for JSON export (default: components_list.json) |
| `--page-size` | ❌ | Number of components per page (default: 50) |
| `--include-example-flows` | ❌ | Include example flows in results (default: exclude) |
| `--header-flows` | ❌ | Include header flows |
| `--component-id` | ❌ | Get details for a specific component ID |

#### Components Download Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--output-dir` | ❌ | Output directory for downloaded components (default: ./Components) |
| `--page-size` | ❌ | Number of components per page (default: 50) |
| `--include-example-flows` | ❌ | Include example flows in results (default: exclude) |
| `--header-flows` | ❌ | Include header flows |
| `--component-id` | ❌ | Download a specific component by ID |
| `--create-index` | ❌ | Create an index file with all downloaded components |

#### File Upload Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `file_path` | ✅ | Path to the file to upload |
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |

#### Files List Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--export-json` | ❌ | Export files list to JSON file |
| `--output-file` | ❌ | Output file name for JSON export (default: files_list.json) |

#### Upload and Run Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `file_path` | ✅ | Path to the file to upload |
| `--langflow-url` | ❌ | Langflow URL (default: from LANGFLOW_URL env var) |
| `--langflow-token` | ❌ | Langflow API token (default: from LANGFLOW_TOKEN env var) |
| `--flow-id` | ❌ | Flow ID to run (default: from FLOW_ID env var) |
| `--course-id` | ❌ | Course ID for custom component (default: from COURSE_ID env var) |
| `--user-id` | ❌ | User ID for custom component (default: from USER_ID env var) |
| `--input-value` | ❌ | Input value for the flow (default: 'hello world!') |

#### Project Transfer Script Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--source-project-id` | ✅ | Source project ID to transfer from |
| `--target-project-id` | ✅ | Target project ID to transfer to |
| `--source-url` | ❌ | Source Langflow URL (default: from LANGFLOW_SOURCE_URL env var) |
| `--source-token` | ❌ | Source Langflow API token (default: from LANGFLOW_SOURCE_TOKEN env var) |
| `--target-url` | ❌ | Target Langflow URL (default: from LANGFLOW_TARGET_URL env var) |
| `--target-token` | ❌ | Target Langflow API token (default: from LANGFLOW_TARGET_TOKEN env var) |

**💡 Tip:** You can configure all these variables in the `.env` file so you don't need to pass parameters every time!

## Usage Examples

### Backup Script Examples

#### 1. Simple Local Backup

```bash
# With .env file configured
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py --langflow-url http://localhost:3000
```

#### 2. Backup with Custom Directory

```bash
# With .env file configured (OUTPUT_DIR=./my-flows-backup)
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py \
    --langflow-url http://localhost:3000 \
    --output-dir ./my-flows-backup
```

#### 3. Backup and Send to GitHub

```bash
# With .env file configured (PUSH_TO_GITHUB=true)
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-langflow-token \
    --github-repo lucas/langflow-backup \
    --github-token ghp_xxxxxxxxxxxxxxxxxxxx \
    --push-to-github
```

### Import Script Examples

#### 1. List Available Projects

```bash
# With .env file configured
python import_flows.py --list-projects

# Or with direct parameters
python import_flows.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-langflow-token \
    --list-projects
```

#### 2. Import Single Flow

```bash
# Import to default project
python import_flows.py --flow-file my_flow.json

# Import to specific project
python import_flows.py \
    --flow-file my_flow.json \
    --project-id 12345
```

#### 3. Import Multiple Flows

```bash
# Import all JSON files from a directory
python import_flows.py --flow-directory ./flows_to_import

# Import to specific project
python import_flows.py \
    --flow-directory ./flows_to_import \
    --project-id 12345
```

#### 4. Import with Environment Variables

```bash
# Using .env file configuration
python import_flows.py --flow-file my_flow.json

# Or with direct parameters
python import_flows.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-langflow-token \
    --flow-file my_flow.json \
    --project-id 12345
```

#### 5. List Projects

```bash
# Basic project listing
python list_projects.py

# Show detailed project information
python list_projects.py --show-details

# Export projects to JSON file
python list_projects.py --export-json

# Export with custom filename
python list_projects.py --export-json --output-file my_projects.json

# With environment variables
python list_projects.py --show-details --export-json
```

#### 6. List Flows

```bash
# Basic flows listing
python list_flows.py

# Show detailed flow information
python list_flows.py --show-details

# Export flows to JSON file
python list_flows.py --export-json

# List with custom page size
python list_flows.py --page-size 100

# Include example flows
python list_flows.py --include-example-flows

# Get details for specific flow
python list_flows.py --flow-id 12345

# Components only
python list_flows.py --components-only

# Include header flows
python list_flows.py --header-flows

# Export with custom filename
python list_flows.py --export-json --output-file my_flows.json

# With environment variables
python list_flows.py --show-details --export-json
```

#### 7. List Components

```bash
# Basic components listing
python list_components.py

# Show detailed component information
python list_components.py --show-details

# Export components to JSON file
python list_components.py --export-json

# List with custom page size
python list_components.py --page-size 100

# Include example flows
python list_components.py --include-example-flows

# Get details for specific component
python list_components.py --component-id 12345

# Include header flows
python list_components.py --header-flows

# Export with custom filename
python list_components.py --export-json --output-file my_components.json

# With environment variables
python list_components.py --show-details --export-json
```

#### 8. Download Components

```bash
# Download all components to default directory
python download_components.py

# Download to custom directory
python download_components.py --output-dir ./my_components

# Download with custom page size
python download_components.py --page-size 100

# Include example flows
python download_components.py --include-example-flows

# Download specific component
python download_components.py --component-id 12345

# Include header flows
python download_components.py --header-flows

# Create index file with all components
python download_components.py --create-index

# Download with environment variables and create index
python download_components.py --create-index
```

#### 9. Upload Files

```bash
# Upload any file using environment variables
python upload_file.py my_document.pdf

# Upload text file
python upload_file.py my_document.txt

# Upload image file
python upload_file.py my_image.png

# Upload with custom Langflow URL
python upload_file.py my_document.pdf --langflow-url http://localhost:3000

# Upload with custom API token
python upload_file.py my_document.pdf --langflow-token your-api-token

# Upload with all custom parameters
python upload_file.py my_document.pdf \
    --langflow-url http://localhost:3000 \
    --langflow-token your-api-token
```

#### 10. List Files

```bash
# List files using environment variables
python list_files.py

# List files with custom Langflow URL
python list_files.py --langflow-url http://localhost:3000

# List files with custom API token
python list_files.py --langflow-token your-api-token

# Export files list to JSON
python list_files.py --export-json

# Export with custom filename
python list_files.py --export-json --output-file my_files.json

# List files with all custom parameters
python list_files.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-api-token \
    --export-json
```

#### 11. Upload and Run Flow

```bash
# Upload file and run flow using environment variables
python upload_and_run.py my_document.pdf

# Upload and run with custom Langflow URL
python upload_and_run.py my_document.pdf --langflow-url http://localhost:3000

# Upload and run with custom flow ID
python upload_and_run.py my_document.pdf --flow-id your-flow-id

# Upload and run with custom parameters
python upload_and_run.py my_document.pdf \
    --flow-id your-flow-id \
    --course-id your-course-id \
    --user-id your-user-id

# Upload and run with custom input value
python upload_and_run.py my_document.pdf --input-value "Process this document"

# Upload and run with all custom parameters
python upload_and_run.py my_document.pdf \
    --langflow-url http://localhost:3000 \
    --langflow-token your-api-token \
    --flow-id your-flow-id \
    --course-id your-course-id \
    --user-id your-user-id \
    --input-value "Process this document"
```

#### 12. Transfer Project

```bash
# Transfer project using environment variables
python transfer_project.py --source-project-id abc123 --target-project-id def456

# Transfer with custom source and target URLs
python transfer_project.py \
    --source-project-id abc123 \
    --target-project-id def456 \
    --source-url http://source-langflow:3000 \
    --target-url http://target-langflow:3000

# Transfer with custom tokens
python transfer_project.py \
    --source-project-id abc123 \
    --target-project-id def456 \
    --source-token your-source-token \
    --target-token your-target-token

# Transfer with all custom parameters
python transfer_project.py \
    --source-project-id abc123 \
    --target-project-id def456 \
    --source-url http://source-langflow:3000 \
    --source-token your-source-token \
    --target-url http://target-langflow:3000 \
    --target-token your-target-token
```
```

## Project Transfer Script (`transfer_project.py`)

### Description
Script to transfer a specific project from one Langflow installation to another. This script will:
1. Download all flows from the specified project in the source installation
2. Upload each flow to the target installation and project

### Usage
```bash
# Basic usage with environment variables
python transfer_project.py --source-project-id PROJECT_ID --target-project-id PROJECT_ID

# Transfer with custom source and target URLs
python transfer_project.py \
    --source-project-id PROJECT_ID \
    --target-project-id PROJECT_ID \
    --source-url http://source-langflow:3000 \
    --target-url http://target-langflow:3000

# Transfer with custom tokens
python transfer_project.py \
    --source-project-id PROJECT_ID \
    --target-project-id PROJECT_ID \
    --source-token your-source-token \
    --target-token your-target-token
```

### Parameters
- `--source-project-id`: Source project ID to transfer from (required)
- `--target-project-id`: Target project ID to transfer to (required)
- `--source-url`: Source Langflow URL (default: from LANGFLOW_SOURCE_URL env var or http://localhost:3000)
- `--source-token`: Source Langflow API token (default: from LANGFLOW_SOURCE_TOKEN env var)
- `--target-url`: Target Langflow URL (default: from LANGFLOW_TARGET_URL env var or http://localhost:3000)
- `--target-token`: Target Langflow API token (default: from LANGFLOW_TARGET_TOKEN env var)

### Environment Variables
```bash
# Source installation
LANGFLOW_SOURCE_URL=http://source-langflow:3000
LANGFLOW_SOURCE_TOKEN=your-source-token

# Target installation
LANGFLOW_TARGET_URL=http://target-langflow:3000
LANGFLOW_TARGET_TOKEN=your-target-token
```

### Example Output
```
[2024-01-15 10:30:00] 🚀 Starting project transfer...
[2024-01-15 10:30:01] Verifying project abc123 exists in source
[2024-01-15 10:30:02] ✅ Project verified: My Source Project
[2024-01-15 10:30:03] Verifying project def456 exists in target
[2024-01-15 10:30:04] ✅ Project verified: My Target Project
[2024-01-15 10:30:05] 📥 Getting flows from source project abc123...
[2024-01-15 10:30:06] Found 3 flows to transfer

--- Transferring flow 1/3: My Flow 1 (ID: flow123) ---
[2024-01-15 10:30:07] Downloading flow flow123
[2024-01-15 10:30:08] ✅ Downloaded flow: My Flow 1
[2024-01-15 10:30:09] Uploading flow to: http://target-langflow:3000/api/v1/flows/upload/?project_id=def456
[2024-01-15 10:30:10] ✅ Flow uploaded successfully!
[2024-01-15 10:30:11]    New Flow ID: new_flow_789
[2024-01-15 10:30:12]    Flow Name: My Flow 1
[2024-01-15 10:30:13] ✅ Successfully transferred flow: My Flow 1

📊 Transfer Summary:
   Total flows: 3
   Successfully transferred: 3
   Failed: 0

✅ Project transfer completed! 3 flows transferred successfully.
```
```

## Generated Files Structure

```
langflow_backup/
└── Compressed Backup/
    └── langflow_flows_backup_20240115_103000.zip
```

The ZIP file contains all flows in their original format as exported by the Langflow API.

**Note:** The `backup_flows_individual.py` script generates individual JSON files, while `backup_flows_zip.py` generates a single ZIP file containing all flows.

### Components Download Structure

```
Components/
├── abc123_My_Custom_Component.json
├── def456_Data_Processor.json
├── ghi789_Text_Generator.json
└── components_index.json
```

Each component is saved as an individual JSON file with the format: `{component_id}_{component_name}.json`

The `components_index.json` file contains metadata about all downloaded components for easy reference.

## Configuration

### 1. Langflow Token (Optional)

If your Langflow installation requires authentication:

1. Access your Langflow installation
2. Go to Settings > API Keys
3. Generate a new API Key
4. Use the token with the `--langflow-token` parameter

### 2. GitHub Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (full access to repositories)
4. Copy the generated token

### 3. Create Repository

1. Create a new repository on GitHub
2. Note the name in `owner/repo` format

### 4. Use the Script

```bash
# With .env file configured
python backup_flows_zip.py

# Or with direct parameters
python backup_flows_zip.py \
    --langflow-url http://localhost:3000 \
    --langflow-token your-langflow-token \
    --github-repo your-username/langflow-backup \
    --github-token ghp_xxxxxxxxxxxxxxxxxxxx \
    --push-to-github
```

## Langflow APIs Used

### Backup Script
- `GET /api/v1/flows` - Lists all flows
- `POST /api/v1/flows/download/` - Exports flows as ZIP

### Import Script
- `GET /api/v1/projects/` - Lists available projects
- `POST /api/v1/flows/upload/` - Imports flow from JSON file

### Projects List Script
- `GET /api/v1/projects/` - Lists all projects with details

### Flows List Script
- `GET /api/v1/flows/` - Lists flows with pagination and filtering
- `GET /api/v1/flows/{id}` - Gets details for specific flow

### Components List Script
- `GET /api/v1/flows/` - Lists components with pagination and filtering (components_only=True)
- `GET /api/v1/flows/{id}` - Gets details for specific component

### Components Download Script
- `GET /api/v1/flows/` - Lists components with pagination and filtering (components_only=True)
- `GET /api/v1/flows/{id}` - Gets details for specific component

### File Upload Script
- `POST /api/v2/files` - Upload any file type to Langflow

### Files List Script
- `GET /api/v2/files` - List all files from Langflow

### Upload and Run Script
- `POST /api/v2/files` - Upload any file type to Langflow
- `POST /api/v1/run/{flow_id}` - Run Langflow flow with uploaded file

### Project Transfer Script
- `GET /api/v1/projects/{id}` - Verify project exists in source and target
- `GET /api/v1/flows/` - Get all flows from source project with pagination
- `GET /api/v1/flows/{id}` - Download specific flow as JSON
- `POST /api/v1/flows/upload/` - Upload flow to target installation

## Error Handling

The script includes robust error handling:

- ✅ Langflow connection unavailable
- ✅ Flows not found
- ✅ GitHub authentication errors
- ✅ Network problems
- ✅ Corrupted files

## Logs

The script generates detailed logs with timestamp:

```
[2024-01-15 10:30:00] Starting Langflow flows backup...
[2024-01-15 10:30:01] Searching flows at: http://localhost:3000/api/v1/flows
[2024-01-15 10:30:02] Found 5 flows
[2024-01-15 10:30:03] Saved: my_flow_1_abc123.json
[2024-01-15 10:30:04] Saved: my_flow_2_def456.json
[2024-01-15 10:30:05] Backup completed! 5 flows saved in: ./langflow_backup
```

## Flow Restoration

To restore a flow from backup:

1. **Via Langflow API:**
   ```bash
   curl -X POST http://localhost:3000/api/v1/flows \
     -H "Content-Type: application/json" \
     -d @flow_example_1_abc123.json
   ```

2. **Via Web Interface:**
   - Access your Langflow installation
   - Go to "Import Flow"
   - Select the JSON file from backup

## Troubleshooting

### Langflow Connection Error

```
[ERROR] Error searching flows: Connection refused
```

**Solution:** Check if Langflow is running and accessible at the provided URL.

### Langflow Authentication Error

```
[ERROR] Authentication error. Check if the Langflow token is correct.
```

**Solution:** Check if the Langflow token is correct or if it's necessary for your installation.

### GitHub Authentication Error

```
[ERROR] Error sending to GitHub: 401 Unauthorized
```

**Solution:** Check if the GitHub token is correct and has the necessary permissions.

### Repository Not Found Error

```
[ERROR] Error sending to GitHub: Repository not found
```

**Solution:** Check if the repository exists and you have access to it.

## Contribution

Feel free to contribute with improvements:

1. Fork the project
2. Create a branch for your feature
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is under MIT license. See the LICENSE file for more details. 