import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from app.auth import get_password_hash
except ImportError as e:
    print(f"Error: Tidak dapat mengimpor modul yang dibutuhkan. Pastikan Anda menjalankan ini dari root direktori proyek.")
    print(f"Detail error: {e}")
    sys.exit(1)

def main():
    """
    Script command-line untuk membuat hash password dan menghasilkan perintah SQL INSERT.
    """
    parser = argparse.ArgumentParser(description="Buat user baru untuk P-APP.")
    parser.add_argument("username", type=str, help="Username untuk user baru.")
    parser.add_argument("password", type=str, help="Password untuk user baru.")
    
    args = parser.parse_args()
    
    username = args.username
    password = args.password
    
    hashed_password = get_password_hash(password)
    
    print("\n" + "="*50)
    print("Perintah SQL untuk membuat user baru:")
    print("="*50)
    print(f"INSERT INTO users (username, hashed_password, is_active) VALUES ('{username}', '{hashed_password}', true);")
    print("="*50)
    print("\nSalin perintah di atas dan jalankan di dalam psql.")

if __name__ == "__main__":
    main()
