import os
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def download_file(args):
    url, file_path = args
    try:
        # Download to temporary location first, then overwrite
        temp_dest = file_path.with_name(file_path.name + ".tmp")
        urllib.request.urlretrieve(url, temp_dest)
        temp_dest.replace(file_path)
        print(f"Successfully restored {file_path}", flush=True)
        return True
    except Exception as e:
        print(f"Error restoring LFS file {file_path}: {e}", flush=True)
        return False

def main():
    print("Checking for Git LFS pointers to restore...", flush=True)
    
    paths_to_check = [
        Path("/app/Backend/data"),
        Path("/models"),
        Path("/usr/sbin/nginx")
    ]
    
    tasks = []
    
    for path in paths_to_check:
        if not path.exists():
            continue
        
        if path.is_file():
            files = [path]
        else:
            files = [p for p in path.rglob("*") if p.is_file()]
            
        for file_path in files:
            try:
                # Check if it's a small file and contains the LFS header
                if file_path.stat().st_size < 1000:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        header = f.read(100)
                    if "version https://git-lfs.github.com/spec/v1" in header:
                        # Determine the repository relative path
                        if file_path.as_posix().startswith("/app/"):
                            repo_rel_path = file_path.relative_to("/app").as_posix()
                        elif file_path.as_posix().startswith("/models/"):
                            repo_rel_path = "triton/model_repository/" + file_path.relative_to("/models").as_posix()
                        elif file_path.as_posix() == "/usr/sbin/nginx":
                            repo_rel_path = "docker/nginx-runtime/nginx"
                        else:
                            print(f"Warning: Unknown mapping for LFS file {file_path}", flush=True)
                            continue
                            
                        url = f"https://huggingface.co/spaces/Nagarohit/stad-ai/resolve/main/{repo_rel_path}"
                        tasks.append((url, file_path))
            except Exception as e:
                print(f"Error checking file {file_path}: {e}", flush=True)
                
    if tasks:
        print(f"Found {len(tasks)} LFS files to download. Starting download in parallel...", flush=True)
        with ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(download_file, tasks))
        success_count = sum(1 for r in results if r)
        print(f"LFS restore completed. Successfully restored {success_count}/{len(tasks)} files.", flush=True)
    else:
        print("No LFS files found to restore.", flush=True)

if __name__ == "__main__":
    main()
