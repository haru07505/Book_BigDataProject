"""Normalize raw book records from Tiki and Fahasa into one schema."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import html
from pathlib import Path
from typing import Any
from datetime import datetime


FIELDS = [
    "book_id",
    "source",
    "title",
    "author",
    "publisher",
    "language_group",
    "main_category",
    "sub_category",
    "price",
    "original_price",
    "discount_rate",
    "rating",
    "review_count",
    "sold_count",
    "publish_year",
    "page_count",
    "url",
]

CATEGORY_MAPPING = {
    # Văn học
    "sach van hoc": "Văn học",
    "fiction literature": "Văn học",
    "van hoc": "Văn học",
    "fiction": "Văn học",

    # Thiếu nhi
    "children s books": "Thiếu nhi",
    "thieu nhi": "Thiếu nhi",
    "sach thieu nhi": "Thiếu nhi",

    # Tâm lý
    "sach tam ly gioi tinh": "Tâm lý - Kỹ năng sống",
    "tam ly ky nang song": "Tâm lý - Kỹ năng sống",
    "personal development": "Tâm lý - Kỹ năng sống",
    "how to self help": "Tâm lý - Kỹ năng sống",
    "mind body spirit": "Tâm lý - Kỹ năng sống",
    "sach ky nang song": "Tâm lý - Kỹ năng sống",
    "popular psychology": "Tâm lý - Kỹ năng sống",

    # Giáo khoa
    "giao khoa tham khao": "Giáo khoa - Tham khảo",
    "education teaching": "Giáo khoa - Tham khảo",
    "education reference": "Giáo khoa - Tham khảo",

    # Ngoại ngữ
    "sach hoc ngoai ngu": "Sách học ngoại ngữ",
    "other languages": "Sách học ngoại ngữ",
    
    #Từ điển
    "dictionaries languages": "Từ điển & Ngôn ngữ",
    "dictionary": "Từ điển",
    
    # Kinh tế
    "kinh te": "Kinh tế",
    "business finance management": "Kinh tế",
    "business economics": "Kinh tế",
    "sach kinh te": "Kinh tế",

    # Công nghệ thông tin
    "sach cong nghe thong tin": "Công nghệ thông tin",
    "computing": "Công nghệ thông tin",

    # Khoa học - Công nghệ
    "science technology": "Khoa học - Công nghệ",
    "technology engineering": "Khoa học - Công nghệ",
    "science geography": "Khoa học - Công nghệ",

    # Manga - Comic
    "graphic novels anime manga": "Manga - Comic",
    "manga comic": "Manga - Comic",
    "truyen tranh manga comic": "Manga - Comic",
    "comics graphic novels": "Manga - Comic",

    # Tiểu sử - Hồi ký
    "tieu su hoi ky": "Tiểu sử - Hồi ký",
    "biography": "Tiểu sử - Hồi ký",
    "biographies memoirs": "Tiểu sử - Hồi ký",

    # Tạp chí
    "tap chi catalogue": "Tạp chí",
    "magazines": "Tạp chí",

    # Gia đình - Đời sống
    "sach thuong thuc gia dinh": "Gia đình - Đời sống",
    "crafts and hobbies": "Gia đình - Đời sống",
    "home garden": "Gia đình - Đời sống",
    "home living": "Gia đình - Đời sống",
    
    # Y học - Sức khỏe
    "sach y hoc": "Y học - Sức khỏe",
    "health": "Y học - Sức khỏe",
    "medical books": "Y học - Sức khỏe",
    "health fitness sports": "Y học - Sức khỏe",

    # Văn hóa - Xã hội
    "sach van hoa dia ly du lich": "Văn hóa - Xã hội",
    "history politics social sciences": "Văn hóa - Xã hội",
    "society social sciences": "Văn hóa - Xã hội",
    "encyclopedia": "Văn hóa - Xã hội",
    "religion culture": "Văn hóa - Xã hội",

    # Văn hóa - Xã hội mở rộng
    "sach chinh tri phap ly": "Văn hóa - Xã hội",
    "history archaeology": "Văn hóa - Xã hội",
    "sach lich su": "Văn hóa - Xã hội",
    "natural history": "Văn hóa - Xã hội",
    "travel holiday": "Văn hóa - Xã hội",
    "sach kien thuc tong hop": "Văn hóa - Xã hội",
    "religion": "Văn hóa - Xã hội",
    "sach ton giao tam linh": "Văn hóa - Xã hội",
    "arts literature": "Văn học",

    # Nghệ thuật
    "dien anh nhac hoa": "Nghệ thuật - Nhiếp ảnh",


    # Nuôi dạy con
    "nuoi day con": "Nuôi dạy con",
    "parenting relationships": "Nuôi dạy con",

    # Ẩm thực
    "cookbooks food wine": "Ẩm thực",
    "food drink": "Ẩm thực",
    
    # Nghệ thuật
    "art photography": "Nghệ thuật - Nhiếp ảnh",

    # Thể thao
    "the duc the thao": "Thể dục Thể thao - Giải trí",
    "humour": "Thể dục Thể thao - Giải trí",
    "entertainment": "Thể dục Thể thao - Giải trí",

    # Văn học mở rộng
    "dam my": "Văn học",
    "science fiction fantasy horror": "Văn học",
    "romance": "Văn học",
    "poetry drama": "Văn học",
    "crime thriller": "Văn học",
}

SUBCATEGORY_MAPPING = {
    "tieu thuyet": "Tiểu thuyết",
    "tieu thuyet phuong tay": "Tiểu thuyết phương Tây",

    "picture books": "Picture Books",
    "truyen tranh thieu nhi": "Truyện tranh thiếu nhi",

    "luyen thi ielts": "Luyện thi IELTS",
    "luyen thi toeic": "Luyện thi TOEIC",
    "luyen thi toefl": "Luyện thi TOEFL",

    "cam nang lam cha me": "Cẩm nang làm cha mẹ",
    "kien thuc bach khoa": "Kiến thức bách khoa",
    "kien thuc bach khoa": "Kiến thức bách khoa",

    "family relationships": "Family & Relationships",
    "family relationship": "Family & Relationships",

    "tac pham kinh dien": "Tác phẩm kinh điển",
    "du ky": "Du ký",
}

PUBLISHER_MAPPING = {
    "phidal publishing inc": "Phidal Publishing",
    "phidal publishing": "Phidal Publishing",
    
    # Nhà Xuất Bản Trẻ
    "nxb tre": "Nhà Xuất Bản Trẻ",
    "tre": "Nhà Xuất Bản Trẻ",

    # Nhà Xuất Bản Thế Giới
    "nha xuat ban the gioi": "Nhà Xuất Bản Thế Giới",
    "the gioi": "Nhà Xuất Bản Thế Giới",
    "nxb the gioi": "Nhà Xuất Bản Thế Giới",
    "the gioi publisher": "Nhà Xuất Bản Thế Giới",

    # Nhà Xuất Bản Dân Trí
    "dan tri": "Nhà Xuất Bản Dân Trí",
    "nha xuat ban dan tri": "Nhà Xuất Bản Dân Trí",
    "nxb dan tri": "Nhà Xuất Bản Dân Trí",
    "dan tri publishing": "Nhà Xuất Bản Dân Trí",

    # Nhà Xuất Bản Kim Đồng
    "kim dong": "Nhà Xuất Bản Kim Đồng",
    "nha xuat ban kim dong": "Nhà Xuất Bản Kim Đồng",
    "nxb kim dong": "Nhà Xuất Bản Kim Đồng",

    # Nhà Xuất Bản Hà Nội
    "nha xuat ban ha noi": "Nhà Xuất Bản Hà Nội",
    "ha noi": "Nhà Xuất Bản Hà Nội",
    "nxb ha noi": "Nhà Xuất Bản Hà Nội",

    # Nhà Xuất Bản Đại Học Quốc Gia Hà Nội
    "dai hoc quoc gia ha noi": "Nhà Xuất Bản Đại Học Quốc Gia Hà Nội",
    "nha xuat ban dai hoc quoc gia ha noi": "Nhà Xuất Bản Đại Học Quốc Gia Hà Nội",
    "nxb dai hoc quoc gia ha noi": "Nhà Xuất Bản Đại Học Quốc Gia Hà Nội",
    "dhqg ha noi": "Nhà Xuất Bản Đại Học Quốc Gia Hà Nội",

    # Nhà Xuất Bản Văn Học
    "van hoc": "Nhà Xuất Bản Văn Học",
    "nha xuat ban van hoc": "Nhà Xuất Bản Văn Học",

    # Nhà Xuất Bản Hồng Đức
    "nha xuat ban hong duc": "Nhà Xuất Bản Hồng Đức",
    "hong duc": "Nhà Xuất Bản Hồng Đức",
    "nxb hong duc": "Nhà Xuất Bản Hồng Đức",
    
    # Nhà Xuất Bản Tổng Hợp TP.HCM
    "nha xuat ban tong hop tp hcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "nxb tong hop tphcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "tong hop thanh pho ho chi minh": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "tong hop tphcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "tong hop tp hcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "nxb tong hop thanh pho ho chi minh": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "tong hop ho chi minh": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "nxb tong hop tp hcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",
    "nxb tong hop tphcm": "Nhà Xuất Bản Tổng Hợp TP.HCM",

    # Nhà Xuất Bản Lao Động
    "nha xuat ban lao dong": "Nhà Xuất Bản Lao Động",
    "lao dong": "Nhà Xuất Bản Lao Động",
    "nxb lao dong": "Nhà Xuất Bản Lao Động",

    # Nhà Xuất Bản Công Thương
    "nha xuat ban cong thuong": "Nhà Xuất Bản Công Thương",
    "cong thuong": "Nhà Xuất Bản Công Thương",

    # Nhà Xuất Bản Phụ Nữ Việt Nam
    "nha xuat ban phu nu viet nam": "Nhà Xuất Bản Phụ Nữ Việt Nam",
    "phu nu viet nam": "Nhà Xuất Bản Phụ Nữ Việt Nam",
    "nxb phu nu viet nam": "Nhà Xuất Bản Phụ Nữ Việt Nam",
    "nha xuat ban phu nu": "Nhà Xuất Bản Phụ Nữ Việt Nam",
    "phu nu": "Nhà Xuất Bản Phụ Nữ Việt Nam",
    "nxb phu nu": "Nhà Xuất Bản Phụ Nữ Việt Nam",

    # Nhà Xuất Bản Thanh Niên
    "thanh nien": "Nhà Xuất Bản Thanh Niên",
    "nxb thanh nien": "Nhà Xuất Bản Thanh Niên",
    "nha xuat ban thanh nien": "Nhà Xuất Bản Thanh Niên",

    # HarperCollins
    "harpercollins": "HarperCollins",
    "harper collins": "HarperCollins",
    "harpercollins publishers": "HarperCollins",
    "harper collins publishers": "HarperCollins",
    "harpercollins us": "HarperCollins",
    "harpercollins publishers inc": "HarperCollins",
    "harpercollins publishers ltd": "HarperCollins",
    "harpercollins leadership": "HarperCollins",
    "harpercollinsireland": "HarperCollins",
    "harpercollins s": "HarperCollins",
    "harper collins- usborne": "HarperCollins",
    "harper collins publ. uk": "HarperCollins",

    # Simon & Schuster
    "simon and schuster": "Simon & Schuster",
    "simon schuster": "Simon & Schuster",
    "simon & schuster": "Simon & Schuster",
    "simon schuster uk": "Simon & Schuster",
    
    # Macmillan
    "macmillan": "Macmillan",
    "mac millan": "Macmillan",
    
    # Scholastic
    "scholastic": "Scholastic",
    "scholastic press": "Scholastic",
    "scholastic inc": "Scholastic",
    
    # Usborne
    "usborne": "Usborne Publishing",
    "usborne publishing": "Usborne Publishing",
    "usborne publishing ltd": "Usborne Publishing",
    "usborne books": "Usborne Publishing",
    
    # DK
    "dk": "DK Publishing",
    "dk publishing": "DK Publishing",
    
    # Harvard Business Review
    "harvard business review": "Harvard Business Review Press",
    "harvard business review press": "Harvard Business Review Press",
    
    # Puffin
    "puffin": "Puffin Books",
    "puffin books": "Puffin Books",
    
    # Hachette
    "hachette": "Hachette",
    "hachette books": "Hachette",
    "hachette book group": "Hachette",
    
    # ELI
    "eli": "ELI Publishing",
    "eli publishing": "ELI Publishing",
    
    # Taschen
    "taschen": "Taschen",
    "taschen publishing": "Taschen",
    
    # Penguin Books
    "penguin us": "Penguin Books",
    "penguin group us": "Penguin Books",
    "penguin group": "Penguin Books",
    "penguin publishing group": "Penguin Books",
    "penguin": "Penguin Books",

    # Nhà Xuất Bản Tri Thức
    "tri thuc": "Nhà Xuất Bản Tri Thức",
    "nha xuat ban tri thuc": "Nhà Xuất Bản Tri Thức",
    
    # Nhà Xuất Bản Hội Nhà Văn
    "hoi nha van": "Nhà Xuất Bản Hội Nhà Văn",

    # Nhà Xuất Bản Đại Học Huế
    "dai hoc hue": "Nhà Xuất Bản Đại Học Huế",

    # Nhà Xuất Bản Đại Học Sư Phạm
    "dai hoc su pham": "Nhà Xuất Bản Đại Học Sư Phạm",
    "nxb dai hoc su pham": "Nhà Xuất Bản Đại Học Sư Phạm",
    "nha xuat ban dai hoc su pham": "Nhà Xuất Bản Đại Học Sư Phạm",

    # Bloomsbury
    "bloomsbury publishing": "Bloomsbury",
    "bloomsbury publishing plc": "Bloomsbury",
    "bloomsbury": "Bloomsbury",
    

    # Cambridge University Press
    "cambridge university": "Cambridge University Press",
    "cambridge university press": "Cambridge University Press",
    "cambridge university press and assessment": "Cambridge University Press",
    "cambridge university press & assessment": "Cambridge University Press",
    "cambridge": "Cambridge University Press",

    # Nhà Xuất Bản Đà Nẵng
    "da nang": "Nhà Xuất Bản Đà Nẵng",
    "nha xuat ban da nang": "Nhà Xuất Bản Đà Nẵng",
    "nxb da nang": "Nhà Xuất Bản Đà Nẵng",

    # Unknown
    "dang cap nhat": "Unknown",
    ".": "Unknown",
    "oem": "Unknown",
    "unknown": "Unknown",
    "khong co": "Unknown",
    "2018": "Unknown",
    
    # Nhiều NXB
    "nhieu nha xuat ban": "Nhiều Nhà Xuất Bản",
    
    # Nhà Xuất Bản Giáo Dục Việt Nam
    "giao duc viet nam": "Nhà Xuất Bản Giáo Dục Việt Nam",
    "nxb giao duc viet nam": "Nhà Xuất Bản Giáo Dục Việt Nam",
    
    #Nhà Xuất Bản Lao Động Xã Hội
    "nxb lao dong xa hoi": "Nhà Xuất Bản Lao Động Xã Hội",
    "nha xuat ban lao dong xa hoi": "Nhà Xuất Bản Lao Động Xã Hội",
    
    #Nhà Xuất Bản Văn Học
    "nxb van hoc": "Nhà Xuất Bản Văn Học",
    
    #Nhà Xuất Bản Chính Trị Quốc Gia Sự Thật
    "chinh tri quoc gia su that":
    "Nhà Xuất Bản Chính Trị Quốc Gia Sự Thật",
    
    #Nhà Xuất Bản Công Thương
    "nxb cong thuong": "Nhà Xuất Bản Công Thương",
    
    #Nhà Xuất Bản Văn Hóa - Văn Nghệ
    "nxb van hoa van nghe":
    "Nhà Xuất Bản Văn Hóa - Văn Nghệ",
    "nha xuat ban van hoa van nghe tp hcm":
    "Nhà Xuất Bản Văn Hóa - Văn Nghệ",
    
    #Nhà Xuất Bản Khoa Học Xã Hội
    "khoa hoc xa hoi":
    "Nhà Xuất Bản Khoa Học Xã Hội",
    
    # Nhà Xuất Bản Văn Hoá Thông Tin
    "nxb van hoa thong tin":
    "Nhà Xuất Bản Văn Hoá Thông Tin",
    
    # Nhà Xuất Bản Thể Dục Thể Thao
    "nha xuat ban the duc the thao": "Nhà Xuất Bản Thể Dục Thể Thao",
    # Nhà Xuất Bản Văn Hóa - Văn Nghệ
    "nha xuat ban van hoa van nghe": "Nhà Xuất Bản Văn Hóa - Văn Nghệ",
    
        # Nhà Xuất Bản Từ Điển Bách Khoa
    "nha xuat ban tu dien bach khoa":
        "Nhà Xuất Bản Từ Điển Bách Khoa",
    "nxb tu dien bach khoa":
        "Nhà Xuất Bản Từ Điển Bách Khoa",
        
    # Báo / công ty Việt Nam
    "bao sinh vien vn hoa hoc tro": "Báo Sinh Viên Việt Nam - Hoa Học Trò",
    "cong ty tnhh khong gian song media": "Công Ty TNHH Không Gian Sống Media",

    # Nhà Xuất Bản Y Học
    "nha xuat ban y hoc":
        "Nhà Xuất Bản Y Học",
    "nxb y hoc":
        "Nhà Xuất Bản Y Học",

    # Nhà Xuất Bản Tài Chính
    "nha xuat ban tai chinh":
        "Nhà Xuất Bản Tài Chính",
    "nxb tai chinh":
        "Nhà Xuất Bản Tài Chính",
    "tai chinh":
        "Nhà Xuất Bản Tài Chính",

    # Nhà Xuất Bản Kinh Tế - Tài Chính
    "nha xuat ban kinh te tai chinh":
        "Nhà Xuất Bản Kinh Tế - Tài Chính",

    # Nhà Xuất Bản Hội Nhà Văn
    "nha xuat ban hoi nha van":
        "Nhà Xuất Bản Hội Nhà Văn",
    "nxb hoi nha van":
        "Nhà Xuất Bản Hội Nhà Văn",
        
    # Nhà Xuất Bản Đại Học Sư Phạm TP.HCM
    "dai hoc su pham thanh pho ho chi minh": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "dai hoc su pham tp hcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "dai hoc su pham tphcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "dai hoc su pham tp ho chi minh": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "nxb dai hoc su pham tp hcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "nxb dai hoc su pham tphcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "nha xuat ban dai hoc su pham tphcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    "su pham tp hcm": "Nhà Xuất Bản Đại Học Sư Phạm TP.HCM",
    
    "nxb lao dong ha noi": "Nhà Xuất Bản Lao Động Hà Nội",
    "nxb dh quoc gia tp hcm": "Nhà Xuất Bản Đại Học Quốc Gia TP.HCM",
    
    "public affairs": "PublicAffairs",
    "harper one": "HarperOne",
    "w h allen": "WH Allen",
    "alpha books": "Alphabooks",
    "lady bird": "Ladybird",
    "g p putnams sons": "G.P. Putnam's Sons",
    "teneues publishing uk ltd": "teNeues",
    "macmillan us": "Macmillan",
    "transworld s ltd": "Transworld Publishers",
    "s s saga pres": "S&S/Saga Press",
    
    "picador paper": "Picador",
    "scholastic focus": "Scholastic",
    "workman kids": "Workman Publishing",
    "headline eternal": "Headline Publishing Group",
    "headline home": "Headline Publishing Group",
    "william morrow company": "William Morrow",
    "william morrow paperbacks": "William Morrow",
    "barnes noble classics": "Barnes & Noble",
    "national geographic society": "National Geographic",
    "national geographic kids": "National Geographic",
    "page street kids": "Page Street",
    
    #Oxford University Press
    "oxford university press": "Oxford University Press",
    "oxford university press uk": "Oxford University Press",
    
    #Nhà Xuất Bản Thông Tin Và Truyền Thông
    "nha xuat ban thong tin va truyen thong": "Nhà Xuất Bản Thông Tin Và Truyền Thông",
    "thong tin va truyen thong": "Nhà Xuất Bản Thông Tin Và Truyền Thông",
    
    #Nhà Xuất Bản Thể Thao Và Du Lịch
    "nha xuat ban the thao va du lich": "Nhà Xuất Bản Thể Thao Và Du Lịch",
    "the thao va du lich": "Nhà Xuất Bản Thể Thao Và Du Lịch",
    "nxb the thao va du lich": "Nhà Xuất Bản Thể Thao Và Du Lịch",
    
    #Nhà Xuất Bản Thanh Hoá
    "nha xuat ban thanh hoa": "Nhà Xuất Bản Thanh Hoá",
    "thanh hoa": "Nhà Xuất Bản Thanh Hoá",
    
    #Nhà Xuất Bản Hải Phòng
    "nha xuat ban hai phong": "Nhà Xuất Bản Hải Phòng",
    "hai phong": "Nhà Xuất Bản Hải Phòng",
    
    
    #Nhà Xuất Bản Thông Tấn
    "nha xuat ban thong tan": "Nhà Xuất Bản Thông Tấn",
    "thong tan": "Nhà Xuất Bản Thông Tấn",
    
    #Nhà Xuất Bản Đồng Nai
    "nha xuat ban dong nai": "Nhà Xuất Bản Đồng Nai",
    "dong nai": "Nhà Xuất Bản Đồng Nai",
    "nxb dong nai": "Nhà Xuất Bản Đồng Nai",
    
    #Nhà Xuất Bản Mỹ Thuật
    "nha xuat ban my thuat": "Nhà Xuất Bản Mỹ Thuật",
    "my thuat": "Nhà Xuất Bản Mỹ Thuật",
    "nxb my thuat": "Nhà Xuất Bản Mỹ Thuật",
    
    #Nhà Xuất Bản Quân Đội Nhân Dân
    "nha xuat ban quan doi nhan dan": "Nhà Xuất Bản Quân Đội Nhân Dân",
    "quan doi nhan dan": "Nhà Xuất Bản Quân Đội Nhân Dân",
    
    #Nhà Xuất Bản Công An Nhân Dân
    "nha xuat ban cong an nhan dan": "Nhà Xuất Bản Công An Nhân Dân",
    "cong an nhan dan": "Nhà Xuất Bản Công An Nhân Dân",
    
    # Penguin
    "penguin us": "Penguin",
    "penguin group us": "Penguin",
    "penguin group": "Penguin",
    "penguin publishing group": "Penguin",
    # Penguin Books
    "penguin books uk": "Penguin Books",
    # Penguin Random House
    "penguin random house us": "Penguin Random House",
    "penguin random house uk": "Penguin Random House",
    "penguin random house children s uk": "Penguin Random House",
    # E-Future
    "e future": "E-Future",
    "e future co ltd": "E-Future",
    "e future publishing": "E-Future",
    # Pan Macmillan
    "pan macmillan": "Pan Macmillan",
    "pan mac millan": "Pan Macmillan",
    # Vermilion
    "vermilion": "Vermilion",
    # Portfolio
    "portfolio": "Portfolio",
    # DK Children
    "dk children": "DK Children",
    # Atria
    "atria": "Atria Books",
    "atria books": "Atria Books",
    # Piatkus
    "piatkus": "Piatkus",
    "piatkus books": "Piatkus",
    # Ebury
    "ebury press": "Ebury Publishing",
    "ebury publishing": "Ebury Publishing",
    # Harper Perennial
    "harper perennial": "Harper Perennial",
    # Hinkler
    "hinkler": "Hinkler Books",
    "hinkler books": "Hinkler Books",
    # North Parade
    "north parade": "North Parade Publishing",
    "north parade publishing": "North Parade Publishing",
    # Orion
    "orion": "Orion Publishing",
    "orion books": "Orion Publishing",
    "orion publishing": "Orion Publishing",
    # Arrow
    "arrow": "Arrow Books",
    "arrow books": "Arrow Books",
    # Avon
    "avon": "Avon Books",
    "avon books": "Avon Books",
    # Bantam
    "bantam": "Bantam Books",
    "bantam books": "Bantam Books",
    "bantam press": "Bantam Books",
    # Head of Zeus
    "head of zeus": "Head of Zeus",
    # Kingfisher
    "kingfisher": "Kingfisher Books",
    "kingfisher books": "Kingfisher Books",
    # Abrams
    "abrams": "Abrams Books",
    "abrams books": "Abrams Books",
    # Cornerstone
    "cornerstone": "Cornerstone",
    "cornerstone press": "Cornerstone",
    
    "penguin books ltd": "Penguin Books",
    "wordsworth editions ltd": "Wordsworth Editions",
    "wordsworth": "Wordsworth Editions",
    "thames and hudson": "Thames & Hudson",
    "thames and hudson ltd": "Thames & Hudson",
    "little brown book group": "Little, Brown Book Group",
    "scholastic us": "Scholastic",
    "hachette uk": "Hachette",
    "harper business": "HarperBusiness",
    "harperbusiness": "HarperBusiness",
    
    # Nhà Xuất Bản Đại Học Quốc Gia TP.HCM
    "nxb dai hoc quoc gia tp hcm": "Nhà Xuất Bản Đại Học Quốc Gia TP.HCM",
    "dai hoc quoc gia tp hcm": "Nhà Xuất Bản Đại Học Quốc Gia TP.HCM",
    "dai hoc quoc gia tp ho chi minh": "Nhà Xuất Bản Đại Học Quốc Gia TP.HCM",
    # Nhà Xuất Bản Bách Khoa Hà Nội
    "nxb bach khoa ha noi": "Nhà Xuất Bản Bách Khoa Hà Nội",
    # Nhà Xuất Bản Kinh Tế TP.HCM
    "nxb kinh te tphcm": "Nhà Xuất Bản Kinh Tế TP.HCM",
    "kinh te tp ho chi minh": "Nhà Xuất Bản Kinh Tế TP.HCM",
    # Nhà Xuất Bản Thuận Hóa
    "thuan hoa": "Nhà Xuất Bản Thuận Hóa",
    
        # Việt Nam
    "nxb tri thuc": "Nhà Xuất Bản Tri Thức",
    "nxb chinh tri quoc gia su that": "Nhà Xuất Bản Chính Trị Quốc Gia Sự Thật",
    "nxb the duc the thao": "Nhà Xuất Bản Thể Dục Thể Thao",
    "tan viet": "Tân Việt Books",
    "nha xuat ban kinh te tphcm": "Nhà Xuất Bản Kinh Tế TP.HCM",
    "nha xuat ban tong hop": "Nhà Xuất Bản Tổng Hợp",
    "nxb tong hop": "Nhà Xuất Bản Tổng Hợp",
    "tong hop": "Nhà Xuất Bản Tổng Hợp",
    "nbx dai hoc quoc gia ha noi": "Nhà Xuất Bản Đại Học Quốc Gia Hà Nội",
    
    # English publisher variants
    "simon schuster ltd": "Simon & Schuster",
    "bloomsbury publishing inc": "Bloomsbury",
    "nxb cambridge university": "Cambridge University Press",
    "macmillan publishers": "Macmillan",
    "macmillan publishers ltd": "Macmillan",
    "d k publishing": "DK Publishing",
    
    "grand central": "Grand Central Publishing",
    "flame tree publishing co ltd": "Flame Tree Publishing",
    "adams media corporation": "Adams Media",
    "random house inc": "Random House",
    "random house books": "Random House",
    "random house publishing group": "Random House",
    "john murray": "John Murray Press",
    "john murray ltd": "John Murray Press",
    "dorling kindersley ltd": "Dorling Kindersley",
    "laurence king": "Laurence King Publishing",
    "quercus": "Quercus Publishing",
    "octopus books": "Octopus Publishing",
    "octopus publishing group": "Octopus Publishing",
    "miles kelly publishing ltd": "Miles Kelly Publishing",
    "imagine that publishing ltd": "Imagine That Publishing",
    "kingfisher books ltd": "Kingfisher Books",
    "workman publishing company": "Workman Publishing",
    "anchor": "Anchor Books",
    "berkley": "Berkley Books",
    "headline": "Headline Publishing Group",
    "viz media": "VIZ Media",
    "viz media llc": "VIZ Media",
    "arcturus publishing ltd": "Arcturus",
    "barnes noble inc": "Barnes & Noble",
    "godsfield press ltd": "Godsfield",
    "avery publishing group": "Avery",
    "ecco": "Ecco Press",
    "hardie grant": "Hardie Grant Books",
    "health communications inc": "Health Communications",
    "henry holt and co": "Henry Holt & Company",
    "igloo books ltd": "Igloo Books",
    "images publishing group": "Images Publishing",
    "little tiger press group": "Little Tiger Press",
    "transworld publishers ltd": "Transworld Publishers",
    "hachette intl": "Hachette",
    "hachette usa": "Hachette",
    "hachette book group usa": "Hachette",
    "thames hudson ltd": "Thames & Hudson",
    "vintage books": "Vintage",
    "vintage publishing": "Vintage",
    "little brown books": "Little, Brown Books",
    "little brown and company": "Little, Brown & Company",
    "little brown company": "Little, Brown & Company",
    "kodansha international": "Kodansha",
    "penguin press classics": "Penguin Classics",
    "pan": "Pan Books",
    "scribner book company": "Scribner",
    "ryland peters small ltd": "Ryland, Peters & Small",
    "crown publishing group": "Crown",
    "orion publishing co": "Orion Publishing",
    "arrow books ltd": "Arrow Books",
    "bonnier books ltd": "Bonnier Books",
    "random house business books": "Random House Business",
    "penguin young readers group": "Penguin Young Readers",
    "disney hyperion": "Disney Hyperion",
    "north parade publishing ltd": "North Parade Publishing",
    "andrews mcmeel publishing": "Andrews McMeel Publishing",
    "chicken soup for the soul": "Chicken Soup for the Soul",
    "harperteen": "HarperTeen",
    "disney publishing group": "Disney Press",
    "wordworth editions ltd": "Wordsworth Editions",
    "simon schuster usa": "Simon & Schuster",
    "simon schuster inc": "Simon & Schuster",
    "simon": "Simon & Schuster",
    "oxford": "Oxford University Press",
    "oup oxford": "Oxford University Press",
    "cambridge university press assessment": "Cambridge University Press",
    "hachette livre": "Hachette",
    "hachette go": "Hachette",
    "hachette us": "Hachette",
    "hachette uk distribution": "Hachette",
    "bloomsbury uk": "Bloomsbury",
    "bloomsbury children": "Bloomsbury",
    "bloomsbury paperbacks": "Bloomsbury",
    "bloomsbury continuum": "Bloomsbury",
    "bloomsbury circus": "Bloomsbury",
    
    # Random House
    "random house uk": "Random House",
    "random house usa inc": "Random House",
    "random house us": "Random House",
    "random house trade": "Random House",
    "random house trade paperbacks": "Random House",
    "random house childrens books": "Random House",
    "random house books for young readers": "Random House",
    "cengage": "Cengage Learning",
    "cengage learning custom publishing": "Cengage Learning",
    "pearson education": "Pearson",
    "pearson longman": "Pearson",
    "pearson scott foresman": "Pearson",
    "portfolio usa": "Portfolio",
    "portfolio penguin": "Portfolio",
    "hinkler pty ltd": "Hinkler Books",
    "hodder stoughton general division": "Hodder & Stoughton",
    "kodansha comics": "Kodansha",
    "taschen america llc": "Taschen",
    "thames hudson ltd 2001 02": "Thames & Hudson",
    "s s simon element": "Simon Element",
    "periplus editions berkeley books pte ltd": "Periplus Editions",
}

AUTHOR_MAPPING = {
    "nhieu tac gia": "Nhiều Tác Giả",
    "nhieu": "Nhiều Tác Giả",
    "many authors": "Nhiều Tác Giả",
    "collectif": "Nhiều Tác Giả",
    "nhom tac gia": "Nhiều Tác Giả",
    
    "phidal publishing inc": "Phidal Publishing",
    "phidal publishing": "Phidal Publishing",
    
    "edited": "Unknown",
    "khuong le binh": "Khương Lệ Bình",
    "harvard business review": "Harvard Business Review",
    
    "j k rowling": "J.K. Rowling",
    "jk rowling": "J.K. Rowling",
    "j k rowling": "J.K. Rowling",

    "thich nhat hanh": "Thích Nhất Hạnh",
    "robert t kiyosaki": "Robert T. Kiyosaki",
    "john c maxwell": "John C. Maxwell",
    "antoine de saint exupery": "Antoine de Saint-Exupéry",
    "charlotte bronte": "Charlotte Brontë",
    "emily bronte": "Emily Brontë",
    "brene brown": "Brené Brown",
    "hector garcia": "Héctor García",
    
    "m scott peck": "M. Scott Peck",
    "michael mccarthy": "Michael McCarthy",
    "viktor e frankl": "Viktor E. Frankl",
    "stephen r covey": "Stephen R. Covey",
    
    "caroline nixon michael tomlinson": "Caroline Nixon, Michael Tomlinson",
    "caroline nixon michael tomlinson": "Caroline Nixon, Michael Tomlinson",
    "do ki sung": "Do Ki-Sung",
    "do ki sung": "Do Ki-Sung",
    "j r r tolkien": "J. R. R. Tolkien",
    "t j klune": "T.J. Klune",
    "tj klune": "T.J. Klune",
    "phidal publishing inc": "Phidal Publishing Inc.",
    "dk smithsonian institution": "DK, Smithsonian Institution",

    "rachel renee russell": "Rachel Renée Russell",
    "cherri moseley janet rees": "Cherri Moseley, Janet Rees",
    "dinh binh dinh trung": "Đình Bình, Đình Trung",
    "mai lan huong ha thanh uyen": "Mai Lan Hương, Hà Thanh Uyên",
    "yasushi date": "Yasushi Date",
    "anne robinson karen saxby": "Anne Robinson, Karen Saxby",
    "bessel van der kolk m d": "Bessel van der Kolk M.D.",
    "freida mcfadden": "Freida McFadden",
    "george s clason": "George S. Clason",
    "richard h thaler": "Richard H. Thaler",
    
    "artbook": "artbook事務局",
    "trung tam nghien cuu tam li tieu hoa": "Trung Tâm Nghiên Cứu Tâm Lí Tiểu Hòa",
    "bs tran thi huyen thao": "BS. Trần Thị Huyên Thảo",
    "xuan phuong": "Xuân Phượng",
    "b k s iyengar": "B. K. S. Iyengar",
    "camilla de la bedoyere": "Camilla De La Bédoyère",

    "daron acemoglu james a robinson":
        "Daron Acemoglu, James A. Robinson",

    "jeffrey j fox": "Jeffrey J. Fox",

    "steven d levitt stephen j dubner":
        "Steven D. Levitt, Stephen J. Dubner",

    "ts regine galanti": "TS. Regine Galanti",
    "r f kuang": "R. F. Kuang",
    "the school of life": "The School of Life",
    "tom butler bowdon": "Tom Butler-Bowdon",
    "joe dispenza dc": "Joe Dispenza DC",
    "niccolo machiavelli": "Niccolò Machiavelli",
    "luis sepulveda": "Luis Sepúlveda",
}

BOOK_FIXES = {
    "8935278608905": {
        "title": 'Thay Đổi Vì Con - "Thuốc Đắng" Tặng Cha Mẹ Thời 4.0 (Tái Bản 2024)',
    },

    "9781422157985": {
        "title": 'HBR\'s 10 Must Reads on Strategy (including featured article "What Is Strategy?" by Michael E. Porter)',
    },

    "9782764348949": {
        "author": "Phidal Publishing",
        "publisher": "Phidal Publishing",
    },
}


LANGUAGE_MAPPING = {
    "vietnamese": "Tiếng Việt",
    "english": "Tiếng Anh",
}


def clean_text(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default

    text = str(value).replace("\x00", "")

    # Remove invisible unicode chars
    text = re.sub(
        r"[\u200e\u200f\u202a\u202b\u202c\u2066\u2067\u2068\u2069\ufeff]",
        "",
        text,
    )

    # Fix patterns like "& a m p;"
    text = re.sub(r"&\s*a\s*m\s*p\s*;", "&", text, flags=re.I)

    # Decode HTML entities
    text = html.unescape(text)

    # Normalize whitespace
    text = " ".join(text.split())

    return text or default


def parse_year(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = clean_text(value, "")
    if not text:
        return default

    text = text.replace("–", "-").replace("—", "-")
    match = re.search(r"\b(?:18|19|20|21)\d{2}\b", text)
    if match:
        year = int(match.group(0))
        current_year = datetime.now().year
        if 1800 <= year <= current_year:
            return year

    match = re.search(r"\b(?:\d{1,2}[./-]){1,2}((?:18|19|20|21)\d{2})\b", text)
    if match:
        year = int(match.group(1))
        current_year = datetime.now().year
        if 1800 <= year <= current_year:
            return year

    return default


def fold_key(value: Any) -> str:
    text = clean_text(value, "") or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.replace("đ", "d").replace("Đ", "D").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_category(value: Any, default: str = "Unknown") -> str:
    text = clean_text(value, default)
    if not text or text == default:
        return default

    key = fold_key(text)
    return CATEGORY_MAPPING.get(key, text)

def normalize_main_category(record: dict[str, Any], default: str = "Unknown") -> str:
    main = normalize_category(record.get("main_category"), default)
    sub_key = fold_key(record.get("sub_category"))
    title_key = fold_key(record.get("title"))

    text_key = f"{sub_key} {title_key}"
    
    if main == "Từ điển":
        if any(k in sub_key for k in [
            "elt",
            "grammar",
            "vocabulary",
            "workbooks",
            "examination practice",
            "english for business",
        ]):
            return "Sách học ngoại ngữ"

    # Manga / Comic ưu tiên cao nhất
    if any(k in text_key for k in [
        "manga",
        "comic",
        "comics",
        "graphic novel",
        "graphic novels",
        "graphic history",
        "dog man",
        "geronimo stilton reporter",
        "super diaper baby",
        "hooky",
        "comics graphic novels",
        "graphic novels manga",
        "manga books",
        "series manga",
    ]):
        return "Manga - Comic"

    # Reference là nhóm quá rộng, cần tách theo sub_category
    if main == "Reference":
        if any(k in sub_key for k in ["psychology"]):
            return "Tâm lý - Kỹ năng sống"

        if any(k in sub_key for k in ["health fitness sports", "health", "fitness"]):
            return "Y học - Sức khỏe"

        if any(k in sub_key for k in ["crafts hobbies", "gardening", "home living"]):
            return "Gia đình - Đời sống"

        if any(k in sub_key for k in ["encyclopedia", "atlases", "history", "social sciences", "religion"]):
            return "Văn hóa - Xã hội"

        if any(k in sub_key for k in ["foreign language reference", "elt", "grammar", "vocabulary", "toeic", "ielts", "toefl"]):
            return "Sách học ngoại ngữ"

        return "Văn hóa - Xã hội"

    # Sách học ngoại ngữ đang lẫn sách ngoại văn theo chủ đề
    if main == "Sách học ngoại ngữ":
        if any(k in sub_key for k in ["food and drink", "food drink", "cookbooks food wine"]):
            return "Ẩm thực"

        if any(k in text_key for k in ["manga", "comic", "anime", "uma musume"]):
            return "Manga - Comic"

        if any(k in sub_key for k in ["humor entertainment", "humour entertainment"]) and any(
            k in title_key for k in ["uma musume", "shinderera", "gurei"]
        ):
            return "Manga - Comic"
        
        if any(k in text_key for k in ["manga", "comic", "anime"]):
            return "Manga - Comic"

        if any(k in sub_key for k in ["food drink", "cookbooks food wine"]):
            return "Ẩm thực"

        if any(k in sub_key for k in ["art", "anime character", "photography", "drawing painting"]):
            return "Nghệ thuật - Nhiếp ảnh"

        if any(k in sub_key for k in ["health fitness sports"]):
            return "Y học - Sức khỏe"

        if any(k in sub_key for k in ["business", "management", "economics", "marketing"]):
            return "Kinh tế"

        if any(k in sub_key for k in ["fiction", "literature", "classic", "romance"]):
            return "Văn học"

        # Religion / Culture nằm sai nhóm
        if any(k in sub_key for k in ["religion culture", "religion spirituality", "religion beliefs"]):
            return "Văn hóa - Xã hội"

    return main


def normalize_sub_category(value: Any, default: str = "Unknown") -> str:
    text = clean_text(value, default)
    if not text or text == default:
        return default

    key = fold_key(text)
    return SUBCATEGORY_MAPPING.get(key, text)

def normalize_publisher(value: Any, default: str = "Unknown") -> str:
    text = clean_text(value, default)
    if not text:
        return default

    key = fold_key(text)

    if key in {"", "unknown", "none", "null", "dang cap nhat", "khong co"}:
        return default

    # Trường hợp đặc biệt vì fold_key(".") -> ""
    if text.strip() in {".", "...", "-", "_"}:
        return default

    if key in PUBLISHER_MAPPING:
        return PUBLISHER_MAPPING[key]

    if text.isupper():
        return text.title()

    return text


def normalize_language(value: Any, default: str = "Unknown") -> str:
    text = clean_text(value, default)

    if not text or text == default:
        return default

    key = fold_key(text)
    return LANGUAGE_MAPPING.get(key, text)


def number(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d.,]*", str(value))
    if not match:
        return default
    text = match.group(0)
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1 or text.count(",") > 1:
        text = text.replace(".", "").replace(",", "")
    elif "," in text:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def integer(value: Any, default: int | None = None) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else default


def tiki_url(value: Any) -> str | None:
    url = clean_text(value)
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://tiki.vn/{url.lstrip('/')}"


def normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    source = clean_text(record.get("source"), "unknown").lower()

    raw_price = number(record.get("price"), 0.0)
    original_price = number(record.get("original_price"), raw_price)

    if original_price is not None and raw_price is not None and original_price < raw_price:
        original_price = raw_price

    discount_rate = number(record.get("discount_rate"))

    if discount_rate is not None:
        discount_rate = abs(discount_rate)

    # If price equals original_price, discount should be 0
    if original_price and raw_price is not None and original_price == raw_price:
        discount_rate = 0.0
    # If discount_rate is missing or invalid, calculate from prices
    elif discount_rate is None and original_price and raw_price is not None:
        discount_rate = max(0.0, round((original_price - raw_price) * 100 / original_price, 2))
    # If discount_rate exceeds 100%, recalculate from prices (likely corrupted data)
    elif discount_rate is not None and discount_rate > 100 and original_price and raw_price is not None:
        discount_rate = max(0.0, round((original_price - raw_price) * 100 / original_price, 2))

    rating = number(record.get("rating"), 0.0)
    if rating is None or rating < 0 or rating > 5:
        rating = 0.0

    publish_year = parse_year(record.get("publish_year"))
    if publish_year is None:
        publish_year = parse_year(record.get("publication_date"))

    page_count = integer(record.get("page_count"))
    if page_count is not None and (page_count <= 0 or page_count > 5000):
        page_count = None

    normalized = {
        "book_id": clean_text(record.get("book_id")),
        "source": source,
        "title": clean_text(record.get("title")),
        "author": normalize_name(record.get("author")),
        "publisher": normalize_publisher(record.get("publisher")),
        "language_group": normalize_language(record.get("language_group")),
        "main_category": normalize_main_category(record),
        "sub_category": normalize_sub_category(record.get("sub_category")),
        "price": raw_price,
        "original_price": original_price,
        "discount_rate": discount_rate or 0.0,
        "rating": rating,
        "review_count": integer(record.get("review_count"), 0),
        "sold_count": integer(record.get("sold_count"), 0),
        "publish_year": publish_year,
        "page_count": page_count,
        "url": tiki_url(record.get("url")) if source == "tiki" else clean_text(record.get("url")),
    }
    
    book_id = normalized["book_id"]
    if book_id in BOOK_FIXES:
        normalized.update(BOOK_FIXES[book_id])
    
    return {field: normalized[field] for field in FIELDS}


def normalize_file(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as file:
        records = json.load(file)
    normalized = [normalize_record(record) for record in records]
    normalized = [r for r in normalized if r is not None]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
    return normalized

def normalize_name(value: Any, default: str = "Unknown") -> str:
    text = clean_text(value, default)
    if not text:
        return default

    # chuẩn hóa dấu phân cách nhiều tác giả
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*;\s*", ", ", text)
    
    # Chuẩn hóa các giá trị rỗng / không rõ tác giả
    key = fold_key(text)
    if key in {"", "unknown", "unknown author", "none", "null"}:
        return default

    if text.strip() in {"...", "."}:
        return default

    # Bỏ role phụ trong author
    text = re.sub(r"\s*\((translator|illustrator|editor|author)\)\s*", "", text, flags=re.I)
    text = re.sub(r",?\s*illustrated by .*$", "", text, flags=re.I)
    text = re.sub(r",?\s*translated by .*$", "", text, flags=re.I)

    key = fold_key(text)

    if key in AUTHOR_MAPPING:
        return AUTHOR_MAPPING[key]
    
    text = re.sub(r"\bDc\b", "DC", text)
    text = re.sub(r"\bPhd\b", "PhD", text)
    text = re.sub(r"\bMd\b", "M.D.", text)

    if text.isupper():
        return text.title()

    return text

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = normalize_file(args.input, args.output)
    print(f"Wrote {len(records)} normalized records to {args.output}")

if __name__ == "__main__":
    main()
