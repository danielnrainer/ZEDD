#!/usr/bin/env python3
"""
Command-line interface for Zenodo uploader
Supports uploading datasets using modular services
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

try:
    # When run as a package
    from .services.metadata import Creator, EDParameters, ZenodoMetadata
    from .services import get_service_factory, initialize_services
    from .services.file_packing import create_zip_from_folder, compute_checksums
except ImportError:
    # When run as a script
    from src.services.metadata import Creator, EDParameters, ZenodoMetadata
    from src.services import get_service_factory, initialize_services
    from src.services.file_packing import create_zip_from_folder, compute_checksums

def parse_args():
    parser = argparse.ArgumentParser(description="Upload data to Zenodo")
    
    # Zenodo specific options
    parser.add_argument("-z", "--zenodo_id", help="zenodo upload key")
    parser.add_argument("-s", "--sandbox", action="store_true", help="use sandbox mode")
    
    # Metadata options
    parser.add_argument("-m", "--metadata", help="json metadata file")
    parser.add_argument("-T", "--title", help="upload title")
    parser.add_argument("-C", "--creator", action="append", help="creator name e.g. 'Doe, John R.'")
    parser.add_argument("-A", "--affiliation", action="append", help="creator affiliation")
    parser.add_argument("-K", "--keyword", action="append", help="keyword to associate")
    parser.add_argument("-D", "--description", help="description")
    
    # File options
    parser.add_argument("-d", "--directory", action="append", help="directory to upload")
    parser.add_argument("-f", "--files", action="append", help="individual files to upload")
    parser.add_argument("-x", "--checksum", action="store_true", help="compute md5 checksum of uploaded files")
    parser.add_argument("-a", "--archive", action="append", help="pack directory to named archive before upload")
    
    return parser.parse_args()

def load_json_metadata(file_path: str) -> dict:
    """Load metadata from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_creators(creators: Optional[List[str]], affiliations: Optional[List[str]]) -> List[Creator]:
    """Process creator names and affiliations into Creator objects"""
    if not creators:
        raise ValueError("At least one creator is required")
    
    creators_list = []
    for i, name in enumerate(creators):
        affiliation = None
        if affiliations:
            # If we have one affiliation, use it for all creators
            # If we have multiple, match them up
            if len(affiliations) == 1:
                affiliation = affiliations[0]
            elif len(affiliations) > i:
                affiliation = affiliations[i]
        
        creators_list.append(Creator(name=name.strip(), affiliation=affiliation))
    
    return creators_list

def main():
    args = parse_args()
    
    # Validate required parameters
    if not args.zenodo_id:
        print("Error: Zenodo upload key (-z/--zenodo_id) is required", file=sys.stderr)
        sys.exit(1)
    
    # Initialize services with API token
    initialize_services(api_token=args.zenodo_id, sandbox=args.sandbox)
    service_factory = get_service_factory()
    
    # Get required services
    upload_service = service_factory.get_upload_service()
    api_service = service_factory.get_repository_api()
    
    if not upload_service or not api_service:
        print("Error: Failed to initialize upload services", file=sys.stderr)
        sys.exit(1)
    
    # Process metadata
    if args.metadata:
        metadata_dict = load_json_metadata(args.metadata)
        # Note: Funding information is disabled in ZenodoMetadata.to_dict()
        # Users need to add funding manually on Zenodo
    else:
        if not args.title or not args.creator or not args.description:
            print("Error: Either metadata file (-m) or title (-T), creator (-C), and description (-D) are required", 
                  file=sys.stderr)
            sys.exit(1)
        
        # Create metadata object
        creators = process_creators(args.creator, args.affiliation)
        metadata_obj = ZenodoMetadata(
            title=args.title,
            description=args.description,
            creators=creators,
            keywords=args.keyword if args.keyword else []
        )
        metadata_dict = metadata_obj.to_dict()
    
    # Process files to upload
    files_to_upload = []
    
    # Handle directories
    if args.directory:
        if args.archive and len(args.archive) != len(args.directory):
            print("Error: Number of archives must match number of directories", file=sys.stderr)
            sys.exit(1)
        
        for i, directory in enumerate(args.directory):
            archive_name = args.archive[i] if args.archive else None
            try:
                zip_path = create_zip_from_folder(directory, archive_name)
                files_to_upload.append(zip_path)
                print(f"Created archive: {zip_path}")
            except Exception as e:
                print(f"Error creating archive for {directory}: {e}", file=sys.stderr)
                sys.exit(1)
    
    # Add individual files
    if args.files:
        if args.archive and len(args.archive) == 1:
            # Pack all files into one archive
            try:
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    for file in args.files:
                        shutil.copy2(file, temp_dir)
                    zip_path = create_zip_from_folder(temp_dir, args.archive[0])
                    files_to_upload.append(zip_path)
                    print(f"Created archive: {zip_path}")
            except Exception as e:
                print(f"Error creating archive for files: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            files_to_upload.extend(args.files)
    
    if not files_to_upload:
        print("Error: No files to upload. Use -d for directories or -f for files", file=sys.stderr)
        sys.exit(1)
    
    # Compute checksums if requested
    if args.checksum:
        print("Computing checksums...")
        try:
            checksums = compute_checksums(files_to_upload)
            for file_path, checksum in checksums.items():
                print(f"{Path(file_path).name}: {checksum}")
        except Exception as e:
            print(f"Error computing checksums: {e}", file=sys.stderr)
            # Continue without checksums
    
    # Upload using the service
    print("Starting upload...")
    
    def progress_callback(progress: int) -> None:
        """Simple progress callback for CLI"""
        print(f"\rProgress: {progress}%", end="", flush=True)
    
    def status_callback(status: str) -> None:
        """Status callback for CLI"""
        print(f"\n{status}")
    
    try:
        # Use the upload service to handle the complete workflow
        for file_path in files_to_upload:
            print(f"\nUploading {Path(file_path).name}...")
            
            # For CLI, we'll use the API service directly for simpler progress tracking
            # Create deposition
            deposition = api_service.create_deposition(metadata_dict)
            deposition_id = deposition['id']
            print(f"Created deposition {deposition_id}")
            
            # Upload file
            result = api_service.upload_file(deposition_id, file_path, progress_callback)
            print(f"\nUpload completed!")
            
            # Print results
            print(f"File uploaded: {result.get('filename', Path(file_path).name)}")
            if 'links' in deposition:
                print(f"Deposition URL: {deposition['links'].get('html', '')}")
        
        print("\n✅ All uploads completed successfully!")
        print("\n⚠️  Manual Steps Required:")
        print("Please visit your records on Zenodo to manually add:")
        print("• Funding information (grants)")
        print("• Creator roles/types for each author")
        print("These features are not fully supported via the API yet.")
        
    except Exception as e:
        print(f"\nError during upload: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
