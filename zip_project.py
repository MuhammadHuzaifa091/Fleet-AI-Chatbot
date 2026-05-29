import os
import zipfile

def zip_project():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(project_dir, "..", "RAG_Chatbot_Prod_Ready.zip")
    
    # Exclude these giant or unnecessary folders/files
    exclude_dirs = {'venv', '.venv', '__pycache__', '.git', 'logs', 'qdrant_storage'}
    exclude_files = {'sync_output.txt', 'deploy_to_pc12.py', 'chat_error.txt'}
    
    print(f"Creating zip file at {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Modify dirs in-place to avoid walking down excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files or file.endswith('.pyc') or file.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_dir)
                zipf.write(file_path, arcname)
                
    print(f"\n🎉 DONE! Aapka project zip ho gaya hai. File Location: {zip_path}")

if __name__ == "__main__":
    zip_project()
