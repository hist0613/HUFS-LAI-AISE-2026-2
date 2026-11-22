"""Role A: 사용자가 허용한 문서의 앞부분만 추출하고 LLM 입력을 구성한다."""

from models import Excerpt, LLMRequest, ScannedFile


def extract_excerpts(source_root: str, files: list[ScannedFile], *,
                     allowed_ids: list[str], max_chars: int) -> list[Excerpt]:
    """선택 파일 중 허용 ID -> TXT/MD/PDF/DOCX 앞부분. max_chars는 파일당 양수.

    TODO: 명시적으로 허용한 파일만 읽기. 미허용 파일은 결과에도 넣지 않는다.
    암호/읽기 불가/지원하지 않는 형식은 text='', error=사유로 반환한다.
    성공은 error=None. allowed_ids에 미선택/없는 ID가 있으면 ValueError.
    """
    raise NotImplementedError("TODO: extract_excerpts")


def build_llm_request(files: list[ScannedFile], output_root: str,
                      excerpts: list[Excerpt]) -> LLMRequest:
    """선택 목록 + 추출 결과 -> 전송 전 검토할 JSON 객체. 네트워크 요청 없음.

    TODO: selected=True만 포함; 출력 하위 폴더는 상대 경로로 수집.
    TODO: 절대 루트 제외, excerpts ID를 선택 목록과 대조하고 오류 항목 제외.
    내용 전송을 허용하지 않으면 excerpts=[]를 전달한다.
    """
    raise NotImplementedError("TODO: build_llm_request")
