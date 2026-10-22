# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 판례 AI 비서 - 데이터 백업 및 복원 서비스 (backup_service.py)
- 무료 클라우드의 임시 파일시스템 특성을 극복하기 위해 메모리 기반 백업/복원 제공
- ZipSlip 보안 취약점 차단 (안전한 파일명 검증)
- 원자적 파일 교체 및 무결성 보장
"""
import io
import os
import zipfile
from datetime import datetime
from typing import Tuple, Dict, Any
import config


BACKUP_FILES = [
    "review_history.db",
    "saved_cases.json",
    "audit_trail.jsonl",
    "tax_rates.json"
]


def create_backup_zip_bytes() -> bytes:
    """현재 시스템의 모든 검토 이력, 보관함, 감사로그, 세율마스터를 ZIP 바이너리로 생성"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in BACKUP_FILES:
            fpath = config.get_data_file_path(fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
    buf.seek(0)
    return buf.getvalue()


def restore_from_backup_zip(zip_bytes: bytes) -> Tuple[bool, str]:
    """
    업로드된 ZIP 백업 파일로부터 데이터 복원
    ZipSlip 취약점 방지: 아카이브 내 파일명이 BACKUP_FILES 허용 목록에 있는 경우만 추출
    """
    if not zip_bytes:
        return False, "백업 파일 데이터가 비어 있습니다."

    try:
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, "r") as zf:
            namelist = zf.namelist()
            restored_count = 0

            for member in namelist:
                basename = os.path.basename(member)
                # 보안 검증: 허용된 백업 파일명인지 확인
                if basename not in BACKUP_FILES:
                    continue

                dest_path = config.get_data_file_path(basename)
                content = zf.read(member)

                # 대상 디렉터리 보장
                dest_dir = os.path.dirname(dest_path)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)

                # 임시 파일 작성 후 원자적 교체
                tmp_path = dest_path + ".tmp"
                with open(tmp_path, "wb") as f:
                    f.write(content)
                if os.path.exists(dest_path):
                    try:
                        os.replace(tmp_path, dest_path)
                    except OSError:
                        # Windows 파일 락 대응
                        os.remove(dest_path)
                        os.rename(tmp_path, dest_path)
                else:
                    os.rename(tmp_path, dest_path)

                restored_count += 1

            if restored_count == 0:
                return False, "유효한 세무 검토 백업 파일이 포함되어 있지 않습니다."

            return True, f"총 {restored_count}개의 데이터 파일이 성공적으로 복원되었습니다."
    except Exception as e:
        return False, f"복원 중 오류가 발생했습니다: {str(e)}"


def get_data_storage_status() -> Dict[str, Any]:
    """현재 데이터 저장소의 상태 및 파일 용량 반환"""
    status = {}
    for fname in BACKUP_FILES + ["obsidian_tax_knowledge.db"]:
        fpath = config.get_data_file_path(fname)
        if os.path.exists(fpath):
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
            status[fname] = {
                "exists": True,
                "size_kb": size_kb,
                "mtime": mtime,
                "path": fpath
            }
        else:
            status[fname] = {
                "exists": False,
                "size_kb": 0,
                "mtime": "-",
                "path": fpath
            }
    return status
