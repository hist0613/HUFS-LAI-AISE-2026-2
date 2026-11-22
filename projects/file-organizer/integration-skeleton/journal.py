"""Role C: 복구에 필요한 최소 JSONL 기록. 일반 로깅 시스템이 아니다."""

from models import JournalEntry


def append_entry(journal_path: str, entry: JournalEntry) -> None:
    """절대 JSONL 경로 + 기록 -> None. TODO: 한 줄 추가 후 내구 저장.

    같은 (job_id, seq_no)는 같은 작업. PENDING/COMMITTED를 차례로 추가한다.
    created_dirs는 이번 작업이 만든 폴더만 기록; 폴더 생성 중 중단도 고려한다.
    """
    raise NotImplementedError("TODO: append_entry")


def read_entries(journal_path: str) -> list[JournalEntry]:
    """절대 JSONL 경로 -> 기록 순서의 전체 목록. TODO: 스키마/상태 전이 검증.

    없는 파일은 FileNotFoundError. 빈 파일은 []; 손상된 기록은 ValueError.
    """
    raise NotImplementedError("TODO: read_entries")
