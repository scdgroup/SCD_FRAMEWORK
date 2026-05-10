import os
import subprocess
import shutil
import csv
import pickle
import re
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from core.my_enums import setup_readline, option_choice, welcome_test, others_choice
from core.ststic import TXT_FOLDER_ID, TMP_DIR, SCOPES

setup_readline()


def authenticate_drive():
    """المصادقة مع Drive وإرجاع الخدمة."""
    creds = None
    # تخزين token.pickle في نفس مجلد هذا الملف
    token_path = os.path.join(os.path.dirname(__file__), "token.pickle")
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                print("Re-authenticating...")
                creds = None
        if not creds:
            # credentials.json يجب أن يكون في نفس مجلد هذا الملف
            creds_file = os.path.join(os.path.dirname(__file__), "credentials.json")
            if not os.path.exists(creds_file):
                print(f"Not Found credentials.json: {creds_file}")
                print(
                    "Please Download it from Google Cloud Console And let it in folder Core"
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)


def get_drive_files(folder_id):
    service = authenticate_drive()
    if not service:
        return []
    results = (
        service.files()
        .list(q=f"'{folder_id}' in parents", fields="files(id, name, webViewLink)")
        .execute()
    )
    return results.get("files", [])


def read_csv(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def write_csv(file_path, data):
    if data:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


def update_documentation():
    folder_id = TXT_FOLDER_ID
    files = get_drive_files(folder_id)
    # print(f"Found {len(files)} files in Drive folder.")
    # for f in files:
    #     print(f"  - {f['name']}")
    csv_file = os.path.join("doc", "information.csv")
    csv_data = read_csv(csv_file) if os.path.exists(csv_file) else []
    existing_names = {row["name"] for row in csv_data}
    print(f"Existing models in CSV: {len(existing_names)}")
    temp_dir = TMP_DIR
    os.makedirs(temp_dir, exist_ok=True)

    # بناء خريطة اسم -> ملف
    file_by_name = {f["name"]: f for f in files}
    added_count = 0

    for name, file_info in file_by_name.items():
        if not name.endswith(".txt"):
            # سيتم التعديل بحيث يحمل كل النماذج حتى اذا لم يكن له وصف في ملف txt
            continue

        base = name[:-4]
        h5_name = None
        h5_file = None
        for fname in file_by_name:
            if fname.startswith(base) and fname.endswith(".h5"):
                h5_name = fname
                h5_file = file_by_name[fname]
                break

        if not h5_file:
            continue

        if h5_name in existing_names:
            continue

        txt_id = file_info.get("id")
        h5_link = h5_file.get("webViewLink")
        txt_path = os.path.join(temp_dir, name)

        # تحميل ملف txt مباشرة باستخدام معرف الملف لتفادي صفحة العرض
        if txt_id:
            txt_url = f"https://drive.google.com/uc?id={txt_id}"
        else:
            txt_url = file_info.get("webViewLink")

        try:
            subprocess.run(
                ["gdown", "--fuzzy", txt_url, "-O", txt_path],
                check=True,
                capture_output=True,
                text=True,
            )
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                desc = f.read().strip()
        except subprocess.CalledProcessError as e:
            print(f"Failed to download txt {name}: {e.stderr}")
            continue
        except Exception as e:
            print(f"Failed to read txt {name}: {e}")
            continue

        if desc:
            csv_data.append(
                {"name": h5_name, "description": desc, "link_model": h5_link}
            )
            existing_names.add(h5_name)
            added_count += 1
            # print(f"Added {h5_name} with description: {desc[:50]}...")
            print(f"Added {h5_name}")
        try:
            os.remove(txt_path)
        except OSError:
            pass

    write_csv(csv_file, csv_data)
    print(f"Total added: {added_count}")
    shutil.rmtree(temp_dir, ignore_errors=True)


def show_models_with_descriptions():
    csv_file = os.path.join("doc", "information.csv")
    if not os.path.exists(csv_file):
        print("CSV file not found.")
        return
    csv_data = read_csv(csv_file)
    models_dir = "/var/log/scdlogs"
    if not os.path.exists(models_dir):
        print("Models directory not found.")
        return

    valid_names = {row.get("name") for row in csv_data if row.get("name")}
    info_by_name = {row.get("name"): row for row in csv_data if row.get("name")}
    local_models = []
    for root, _, files in os.walk(models_dir):
        for f in files:
            if f.endswith(".txt"):
                continue
            if f not in valid_names:
                continue
            file_path = os.path.join(root, f)
            if not os.path.isfile(file_path):
                continue
            rel_path = os.path.relpath(file_path, models_dir)
            type_name = rel_path.split(os.sep)[0] if os.sep in rel_path else "root"
            local_models.append((rel_path, type_name, f))

    if not local_models:
        print("No matching models found under /var/log/scdlogs/.")
        return

    selected_models = []
    models_by_basename = {}
    for rel_path, type_name, basename in local_models:
        models_by_basename.setdefault(basename, []).append((rel_path, type_name))

    for basename, candidates in models_by_basename.items():
        csv_type = info_by_name.get(basename, {}).get("description", "").lower()
        chosen = None
        if len(candidates) == 1:
            chosen = candidates[0]
        else:
            for candidate in candidates:
                if candidate[1].lower() == csv_type:
                    chosen = candidate
                    break
            if chosen is None:
                chosen = candidates[0]
        selected_models.append((chosen[0], chosen[1], basename))

    if not selected_models:
        print("No matching models found under /var/log/scdlogs/.")
        return

    print("=" * 90)
    print(f"{'Name':<45} {'Type':<15} {'Description':<30}")
    print("=" * 90)
    for rel_path, type_name, basename in sorted(selected_models):
        description = info_by_name.get(basename, {}).get(
            "description", "No description"
        )
        print(f"{rel_path:<45} {type_name:<15} {description:<30}")
    print("=" * 90)


def manage_downloads():
    """إدارة تحميل النماذج من CSV."""
    csv_file = os.path.join("doc", "information.csv")
    if not os.path.exists(csv_file):
        print("CSV file not found.")
        return

    csv_data = read_csv(csv_file)
    models_dir = "/var/log/scdlogs"
    if not os.path.exists(models_dir):
        print("Models directory not found.")
        return

    local_models = set()
    for root, _, files in os.walk(models_dir):
        for f in files:
            if not f.endswith(".txt"):
                local_models.add(f)

    print("=" * 100)
    print(f"{'ID':<5} {'Name':<25} {'Description':<45} {'Downloaded'}")
    print("=" * 100)

    for i, row in enumerate(csv_data, 1):
        name = row["name"]
        desc = row["description"]
        downloaded = "Yes" if name in local_models else "No"
        print(f"{i:<5} {name:<25} {desc:<45} {downloaded}")

    print("=" * 100)

    print("\nDownload all (a) or specific (s)?Enter IDs separated by commas (1,2,3):")
    choice = input("SCD/Test/Download> ").strip()
    if choice == "A" or choice == "a":
        download_all_from_csv(csv_data, models_dir)
        return None
    elif choice == "0" or choice == "back":
        return "back"
    else:
        if choice:
            try:
                selected = [int(x.strip()) for x in choice.split(",") if x.strip()]
                download_selected_from_csv(csv_data, selected, models_dir)
                return None
            except ValueError:
                print("Invalid input.")
        else:
            print("Invalid input.")


def download_all_from_csv(csv_data, target_dir):
    for row in csv_data:
        name = row["name"]
        link = row["link_model"]
        desc = row["description"].lower()
        sub_dir = os.path.join(target_dir, desc)
        os.makedirs(sub_dir, exist_ok=True)
        file_id = extract_file_id(link)
        if file_id:
            url = f"https://drive.google.com/uc?id={file_id}"
        else:
            url = link
        print(f"Downloading {name}...")
        cmd = ["gdown", "--fuzzy", url, "-O", os.path.join(sub_dir, name)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Downloaded {name}")
        else:
            print(f"Failed {name}: {result.stderr}")


def download_selected_from_csv(csv_data, indices, target_dir):
    for idx in indices:
        if 1 <= idx <= len(csv_data):
            row = csv_data[idx - 1]
            name = row["name"]
            link = row["link_model"]
            desc = row["description"].lower()
            sub_dir = os.path.join(target_dir, desc)
            os.makedirs(sub_dir, exist_ok=True)
            file_id = extract_file_id(link)
            if file_id:
                url = f"https://drive.google.com/uc?id={file_id}"
            else:
                url = link
            print(f"Downloading {name}...")
            cmd = ["gdown", "--fuzzy", url, "-O", os.path.join(sub_dir, name)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Downloaded {name}")
            else:
                print(f"Failed {name}: {result.stderr}")


def extract_file_id(link):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
    if match:
        return match.group(1)
    return None


def show_models_menu(rad_use):
    welcome_test(rad_use)
    whereme = "Test"
    while True:
        choice = option_choice(whereme)
        if choice == "0":
            return "back"
        elif choice == "1":
            print("Show all models...")
            show_models_with_descriptions()
        elif choice == "2":
            e = manage_downloads()
            if e == "back":
                return "back"
        elif choice == "3":
            update_documentation()
        elif choice == "4" or choice == "exit" or choice == "e":
            print("\nThank you for using SCD Framework. Goodbye!")
            return "exit"
        elif choice != "1" and choice != "2" and choice != "3" and choice != "4":

            others_choice(choice, "test")
        else:
            print("\nInvalid choice.")
