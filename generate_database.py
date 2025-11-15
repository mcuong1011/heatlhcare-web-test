import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any

# --- Constants ---
NUM_DOCTORS = 50
NUM_PATIENTS = 100

MODEL_USER = "accounts.user"
MODEL_PROFILE = "accounts.profile"
# Sử dụng pathlib.Path để xử lý đường dẫn một cách hiện đại và an toàn
OUTPUT_FILE_PATH = Path("database_test/database_data.json")

# Mật khẩu "password123"
PASSWORD_HASH = "pbkdf2_sha256$260000$HQyGxzxfOxv6nLKI8zF$w9Nmz1Rxm1fPY1HzJ2MU7MgKBfTJ1RfF3q9M1wJvXvQ="

# --- Data Lists ---
MALE_FIRST_NAMES = [
    "Văn Anh", "Minh Tuấn", "Đức Cường", "Hữu Dũng", "Quốc Bảo",
    "Duy Anh", "Gia Huy", "Bảo Nam", "Tuấn Anh", "Hoàng Long",
    "Đình Phong", "Thành Trung", "Công Minh", "Phúc Việt", "Minh Dũng",
    "Hoàng Hải", "Gia Khánh", "Quốc Trung", "Văn Nam", "Bảo Long", "Thanh Tùng",
    "Bá Kiên", "Bảo Khánh", "Công Hậu", "Đăng Khoa", "Đình Lộc", "Đức Anh",
    "Đức Duy", "Hải Đăng", "Hạo Nhiên", "Hữu Nghĩa", "Hoàng Bách", "Hùng Cường",
    "Khánh Duy", "Mạnh Dũng", "Minh Hiếu", "Minh Khang", "Minh Quân", "Nam Khánh",
    "Nhật Minh", "Phúc Hưng", "Quang Hải", "Quang Khải", "Quốc Anh", "Quốc Thiên",
    "Tấn Phát", "Tấn Sang", "Thanh Danh", "Thanh Hải", "Thế Anh", "Thiên Ân",
    "Thiện Nhân", "Tiến Đạt", "Trọng Hiếu", "Trung Dũng", "Tuấn Kiệt", "Việt Anh",
    "Xuân Trường", "Đức Thắng", "Gia Bảo", "Hoàng Anh", "Mạnh Hùng", "Ngọc Sơn"
]

MALE_LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
    "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương",
    "Lý", "Đoàn", "Vương", "Trịnh", "Đào", "Tạ", "Mai", "Cao",
    "Trương", "Châu", "Lương", "Phùng", "Thái", "Lại", "Hà", "Tô",
    "Lâm", "Lưu", "Triệu", "Đinh"
]

FEMALE_FIRST_NAMES = [
    "Thị An", "Ngọc Anh", "Thùy Chi", "Minh Dung", "Quỳnh Giang",
    "Phương Hà", "Gia Hạnh", "Hương Hoa", "Bảo Hương", "Khánh Lan",
    "Mỹ Linh", "Diệu Ly", "Thị Mai", "Minh Châu", "Ngọc Nga",
    "Bảo Ngọc", "Phương Thảo", "Quỳnh Trang", "Thị Yến", "Thùy Linh", "Kim Dung",
    "Ánh Dương", "Ánh Hồng", "Bảo Châu", "Bích Thủy", "Cẩm Vân", "Diễm Quỳnh",
    "Đoan Trang", "Hạ Vy", "Hải Yến", "Hiền Chung", "Hoài An", "Hoài Thương",
    "Hồng Diễm", "Khánh An", "Khánh Ngọc", "Kiều Anh", "Kim Ngân", "Lan Hương",
    "Mai Anh", "Mai Phương", "Minh Nguyệt", "Mỹ Tâm", "Ngọc Bích", "Ngọc Diệp",
    "Ngọc Hoa", "Ngọc Trâm", "Nguyệt Ánh", "Nhã Phương", "Nhật Lệ", "Như Quỳnh",
    "Phương Anh", "Phương Chi", "Phương Linh", "Thanh Hà", "Thanh Mai", "Thanh Trúc",
    "Thảo Nguyên", "Thiên Hương", "Thúy An", "Thúy Hiền", "Thùy Dương", "Trà My",
    "Tú Anh", "Tuyết Lan", "Uyên Thư", "Vân Anh", "Vân Khánh", "Yến Nhi"
]

FEMALE_LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng",
    "Bùi", "Hồ", "Ngô", "Dương", "Lý", "Đoàn", "Vương",
    "Trịnh", "Đào", "Tạ", "Mai", "Cao", "Châu", "Phùng", "Lương",
    "Trương", "Thái", "Lại", "Hà", "Tô", "Kiều", "Lâm", "Lưu",
    "Triệu", "Đinh"
]

SPECIALIZATIONS = [
    "Bác sĩ tim mạch", "Bác sĩ da liễu", "Bác sĩ thần kinh", "Bác sĩ nhi",
    "Bác sĩ phẫu thuật chỉnh hình", "Bác sĩ tâm thần", "Bác sĩ phụ khoa",
    "Nha sĩ", "Bác sĩ nhãn khoa", "Bác sĩ tai mũi họng",
]

# Cập nhật tên thành phố, tỉnh có dấu tiếng Việt
CITIES_PROVINCES = [
    "Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Nha Trang",
    "Huế", "Vũng Tàu", "Quy Nhơn", "Thanh Hóa", "Vinh", "Buôn Ma Thuột", "Đà Lạt", "Biên Hòa",
]

DIVISIONS = [
    "Đồng bằng sông Hồng", "Vùng Đông Bắc", "Vùng Tây Bắc", "Bắc Trung Bộ",
    "Nam Trung Bộ", "Tây Nguyên", "Đông Nam Bộ", "Đồng bằng sông Cửu Long",
]

# Cập nhật tên đường, quận/huyện có dấu tiếng Việt
STREETS = [
    "Trần Hưng Đạo", "Nguyễn Huệ", "Lê Lợi", "Phạm Văn Đồng", "Võ Nguyên Giáp",
    "Hai Bà Trưng", "Lý Thường Kiệt", "Quang Trung", "Nguyễn Trãi", "Phố Huế"
]

DISTRICTS = [
    "Ba Đình", "Hoàn Kiếm", "Đống Đa", "Quận 1", "Quận 3", "Bình Thạnh",
    "Sơn Trà", "Hải Châu", "Ninh Kiều", "Tây Hồ"
]

PATIENT_DISTRICTS = [
    "Cầu Giấy", "Tân Bình", "Thanh Khê", "Gò Vấp", "Hai Bà Trưng",
    "Quận 7", "Ngô Quyền", "Thủ Đức", "Hà Đông", "Bình Tân"
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
ALLERGIES = [
    "None", "Dị ứng hải sản", "Dị ứng phấn hoa", "Dị ứng mạt bụi",
    "Dị ứng thuốc (ví dụ: Penicillin)", "Dị ứng thời tiết", "Dị ứng đậu phộng", "Dị ứng lông chó/mèo"
]
MEDICAL_CONDITIONS = [
    "None", "Cao huyết áp", "Tiểu đường", "Hen suyễn", "Tiền sử sốt xuất huyết",
    "Bệnh dạ dày (viêm loét, trào ngược)", "Rối loạn tiền đình", "Bệnh gút (Gout)",
    "Viêm gan B", "Thiếu máu", "Bệnh lý tuyến giáp"
]
MEDICAL_UNIVERSITIES = [
    'Đại học Y Hà Nội', 'Đại học Y Dược Huế', 'Đại học Y Dược TP.HCM'
]

# --- Helper Functions ---

def _slugify(text: str) -> str:
    """
    Chuyển đổi văn bản tiếng Việt có dấu thành "slug" không dấu,
    dùng cho việc tạo email.
    """
    text = text.lower()
    text = text.replace(" ", "_")
    # Xử lý dấu
    replacements = {
        'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'đ': 'd'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def _generate_random_dob(start_year: int, end_year: int) -> str:
    """
    Tạo ngày sinh ngẫu nhiên (DOB) một cách chính xác,
    tránh lỗi ngày không hợp lệ (ví dụ: 30/02).
    """
    start_date = datetime.date(start_year, 1, 1)
    end_date = datetime.date(end_year, 12, 31)
    
    total_days = (end_date - start_date).days
    random_days = random.randint(0, total_days)
    
    dob = start_date + datetime.timedelta(days=random_days)
    return dob.strftime("%Y-%m-%d")


def _create_user(pk: int, role: str, role_id: int) -> Tuple[Dict[str, Any], str]:
    """
    Hàm trợ giúp tạo đối tượng người dùng (user) và trả về dữ liệu
    người dùng cùng với giới tính (để dùng cho profile).
    """
    gender = random.choice(["male", "female"])

    if gender == "male":
        first_name_field = random.choice(MALE_FIRST_NAMES)
        last_name = random.choice(MALE_LAST_NAMES)
    else:
        first_name_field = random.choice(FEMALE_FIRST_NAMES)
        last_name = random.choice(FEMALE_LAST_NAMES)

    # Sử dụng _slugify để tạo email sạch
    first_name_slug = _slugify(first_name_field.split()[-1]) # Lấy tên chính
    last_name_slug = _slugify(last_name)
    
    username = f"{role}{role_id}"
    email = f"{first_name_slug}.{last_name_slug}@example.com"

    user_data: Dict[str, Any] = {
        "model": MODEL_USER,
        "pk": pk,
        "fields": {
            "password": PASSWORD_HASH,
            "username": username,
            "email": email,
            "first_name": first_name_field,
            "last_name": last_name,
            "role": role,
            "is_active": True,
            "date_joined": "2023-01-01T00:00:00Z",
        },
    }
    return user_data, gender


# --- Main Function ---

def generate_data():
    """
    Hàm chính tạo tất cả dữ liệu.
    """
    data: List[Dict[str, Any]] = []
    current_pk = 1

    print(f"Generating {NUM_DOCTORS} doctors...")
    # Generate doctors
    for i in range(1, NUM_DOCTORS + 1):
        user_pk = current_pk
        profile_pk = current_pk

        user_data, gender = _create_user(user_pk, "doctor", i)
        data.append(user_data)

        # Doctor Profile
        spec = random.choice(SPECIALIZATIONS)
        doctor_profile = {
            "model": MODEL_PROFILE,
            "pk": profile_pk,
            "fields": {
                "user": user_pk,
                "phone": f"+84 09 {random.randint(10000000, 99999999)}",
                "dob": _generate_random_dob(1960, 1990), # Sửa lỗi DOB
                "about": f"Tốt nghiệp {random.choice(MEDICAL_UNIVERSITIES)}. {random.randint(5, 20)} năm kinh nghiệm trong {spec}.",
                "specialization": spec,
                "gender": gender,
                "address": f"Số {random.randint(1, 99)}, {random.choice(STREETS)}, {random.choice(DISTRICTS)}",
                "city": random.choice(CITIES_PROVINCES),
                "state": random.choice(DIVISIONS),
                "postal_code": f"{random.randint(100000, 999999)}",
                "country": "Vietnam",
                "price_per_consultation": random.randint(200000, 1000000),
                "is_available": True,
            },
        }
        data.append(doctor_profile)
        current_pk += 1

    print(f"Generating {NUM_PATIENTS} patients...")
    # Generate patients
    for i in range(1, NUM_PATIENTS + 1):
        user_pk = current_pk
        profile_pk = current_pk

        user_data, gender = _create_user(user_pk, "patient", i)
        data.append(user_data)

        # Patient Profile
        # Các đầu số điện thoại mới và phổ biến ở Việt Nam
        patient_phone_prefix = random.choice(['03', '05', '07', '08'])
        patient_profile = {
            "model": MODEL_PROFILE,
            "pk": profile_pk,
            "fields": {
                "user": user_pk,
                "phone": f"+84 {patient_phone_prefix} {random.randint(10000000, 99999999)}", # SĐT thực tế hơn
                "dob": _generate_random_dob(1970, 2025), # Sửa lỗi DOB
                "gender": gender,
                "address": f"Căn hộ {random.randint(101, 909)}, Tòa nhà {random.choice(['A', 'B', 'C'])}{random.randint(1, 5)}, {random.choice(PATIENT_DISTRICTS)}",
                "city": random.choice(CITIES_PROVINCES),
                "state": random.choice(DIVISIONS),
                "postal_code": f"{random.randint(100000, 999999)}",
                "country": "Vietnam",
                "blood_group": random.choice(BLOOD_GROUPS),
                "allergies": random.choice(ALLERGIES),
                "medical_conditions": random.choice(MEDICAL_CONDITIONS),
            },
        }
        data.append(patient_profile)
        current_pk += 1

    # Đảm bảo thư mục (directory) tồn tại trước khi ghi tệp
    OUTPUT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing data to {OUTPUT_FILE_PATH}...")
    with open(OUTPUT_FILE_PATH, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Done. Generated {current_pk - 1} users and profiles.")


if __name__ == "__main__":
    generate_data()