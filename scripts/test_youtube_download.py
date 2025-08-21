#!/usr/bin/env python3
"""
Test script for YouTube download functionality
"""

import sys
import os
import tempfile
import shutil

# Add the components directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'components'))

def test_youtube_download():
    """Test YouTube download functionality"""
    try:
        from multi_modal.multi_modal_input import ChatInput
        
        # Create a test instance
        test_component = ChatInput()
        
        # Test URL (a short, public YouTube video)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short, public video
        
        print("Testing YouTube download functionality...")
        print(f"Test URL: {test_url}")
        
        # Test the download
        try:
            downloaded_file = test_component.download_youtube_media(test_url, "Video")
            print(f"✓ Successfully downloaded: {downloaded_file}")
            
            # Check if file exists and has content
            if os.path.exists(downloaded_file):
                file_size = os.path.getsize(downloaded_file)
                print(f"✓ File size: {file_size} bytes")
                
                # Clean up
                try:
                    os.remove(downloaded_file)
                    print("✓ Cleaned up test file")
                except:
                    pass
                    
                return True
            else:
                print("✗ Downloaded file does not exist")
                return False
                
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running this from the correct directory")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_yt_dlp_installation():
    """Test if yt-dlp is properly installed"""
    try:
        import yt_dlp
        print("✓ yt-dlp is installed")
        print(f"  Version: {yt_dlp.version.__version__}")
        return True
    except ImportError:
        print("✗ yt-dlp is not installed")
        print("  Install with: pip install yt-dlp")
        return False

def main():
    print("YouTube Download Test")
    print("=" * 30)
    
    # Test yt-dlp installation
    print("\n1. Testing yt-dlp installation...")
    yt_dlp_ok = test_yt_dlp_installation()
    
    if not yt_dlp_ok:
        print("\nPlease install yt-dlp first:")
        print("pip install yt-dlp")
        return
    
    # Test YouTube download
    print("\n2. Testing YouTube download...")
    download_ok = test_youtube_download()
    
    if download_ok:
        print("\n✓ All tests passed! YouTube download functionality is working.")
    else:
        print("\n✗ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
