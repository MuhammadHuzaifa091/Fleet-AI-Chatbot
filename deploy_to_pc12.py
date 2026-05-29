import os
import shutil

# Ye un system files ki list hai jo production (PC 12) mein bhejna dangerous hai.
# .env ko isliye roka gaya hai taake PC 12 ka apna live database configuration bilkul safe rahay.
IGNORE_LIST = [
    '.env', 
    'venv', 
    '.venv', 
    '__pycache__', 
    '.git', 
    'qdrant_storage', 
    'logs', 
    'sync_output.txt', 
    'deploy_to_pc12.py'
]

def ignore_files(dir_path, filenames):
    ignored = []
    for f in filenames:
        if f in IGNORE_LIST or f.endswith('.pyc'):
            ignored.append(f)
    return ignored

def deploy():
    print("="*60)
    print("  🚀 DEPLOYMENT SCRIPT: PC 14 (Dev) -> PC 12 (Prod) 🚀 ")
    print("="*60)

    # 1. Ask for Target Directory
    print(">> Target Folder PC 12 par LAN share hona chahiye.")
    pc12_path = input("\nEnter PC 12 Network Path (maslan: \\\\192.168.1.12\\RAG_Chatbot) ya mapped drive (Z:\\): ").strip()
    
    if not pc12_path or not os.path.exists(pc12_path):
        print(f"\n❌ Error: Yeh path '{pc12_path}' abhi PC 14 se access nahi ho raha.")
        print("Sawal/Hal: Kya PC 12 ka RAG_Chatbot folder network par Share hai aur permissions ON hain?")
        input("Press Enter to Exit...")
        return

    source_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Confirmation Alert
    print(f"\nSource (PC 14 / Aapka Local Code): {source_dir}")
    print(f"Target (PC 12 / Production): {pc12_path}")
    print("\n🚨 SAFETY CHECK: Niche di gai files PC 12 par OVERWRITE NAHI hongi:")
    print(", ".join(IGNORE_LIST))
    print("-" * 60)

    confirm = input("Aap testing se mutmain hain? Type 'yes' to start Deployment to PC 12: ").strip().lower()
    if confirm != 'yes':
        print("\n❌ Deployment Cancelled by user.")
        return

    # 3. Execution Phase
    try:
        print("\n⏳ Uploading files to PC 12... please wait...")
        # dirs_exist_ok=True iski madad se existing folders merge hote hain and files replace hojati hain
        shutil.copytree(source_dir, pc12_path, ignore=ignore_files, dirs_exist_ok=True)
        print("\n🎉 SUCCESS! Deployment completed successfully!")
        print(">>> IMPORTANT: Ab PC 12 par ja kar ek martaba server (uvicorn) ko Restart kar dein taake wo naya code utha le.")
    except Exception as e:
        print(f"\n❌ Deployment failed - Error: {e}")

if __name__ == "__main__":
    deploy()
