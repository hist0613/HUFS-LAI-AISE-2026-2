## Local LLM Host

- 프로젝트 진행을 위한 상시 구동 Local LLM Host
- 별도 인증 없이 교내에서만 접속 가능 (방화벽)
- [munekazu/Qwen3.8-Flash-Next-exl3-CMP170HX-64GB](https://huggingface.co/munekazu/Qwen3.8-Flash-Next-exl3-CMP170HX-64GB)

### 명령어 예시

```bash
curl https://oss-japa.hufs.jae.one/v1/chat/completions \
  -s -H "Content-Type: application/json" \
  -d '{
    "model": "placeholder",
    "messages": [
      {
        "role": "user",
        "content": "한국외대 설명 ㄱㄱ"
      }
    ]
  }' | jq '.'
```

### 응답 예시

```json
{
  "id": "cmpl-0473a835d13e4376a079532987e6c15e",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "eos_reason": "stop_token",
      "stop_str": "<|im_end|>",
      "message": {
        "role": "assistant",
        "content": "\n\n# 한국외국어대학교 (Hankuk University of Foreign Studies, HUFS)\n\n## 기본 정보\n- **설립**: 1954년 (한국전쟁 중)\n- **위치**: 서울특별시 동대문구 이문동 (서울캠퍼스), 경기도 용인시 (글로벌캠퍼스)\n- **유형**: 사립 종합대학\n- **별칭**: \"외대\", \"HUFS\"\n\n## 설립 배경\n한국전쟁으로 국가가 혼란스러울 때, **김흥배 박사**가 \"외국어를 아는 인재가 국가 재건에 필요하다\"는 신념으로 설립. 국내 최초의 외국어 전문 종합대학.\n\n## 주요 특징\n\n### 🌍 외국어·국제 분야\n- **45개 이상**의 외국어 학과 운영 (영어, 중국어, 일본어, 프랑스어, 독일어, 스페인어, 아랍어, 러시아어, 베트남어, 우즈베크어, 스와힐리어 등)\n- 국내에서 가장 많은 외국어 학과 보유\n- 통역·번역 대학원(대학원)으로 유명\n- 외교관, 통역사, 국제기구 인력 다수 배출\n\n### 🏫 캠퍼스\n| 캠퍼스 | 위치 | 특징 |\n|--------|------|------|\n| 서울캠퍼스 | 동대문구 이문동 | 인문·사회·어문계열 중심 |\n| 글로벌캠퍼스 | 용인시 처인구 | 자연과학·공학·경영·법학 등 |\n\n### 📚 학부 구성\n- 외국어대학 (30여 개 학과)\n- 통번역대학원\n- 경영·경제·법학·국제지역학\n- 공과대학·자연과학대학 (글로벌캠퍼스)\n- 글로벌지역학대학\n\n## 인지도 & 이미지\n- **\"외국어 명문\"** 으로 60년 이상 인식\n- 과거 서울대·연고대와 함께 상위권 선호 대학\n- 최근 학령인구 감소·학벌서열 변화로 입시 열기 이전보다 다소 완화된 편\n- nonetheless, 통번역·외국어 분야에서는 여전히 **최상위권 인지도**\n\n## 졸업생 진로\n- 외교부·통상부 공무원\n- 대기업 해외영업·법인\n- 국제기구 (UN, WTO, ADB 등)\n- 통역사·번역사\n- 로스쿨·외국어교수·K-콘텐츠 번역\n\n## 한 줄 요약\n> \"한국에서 외국어를 배우고 싶다면, 가장 먼저 떠오르는 이름.\"\n\n---\n\n더 궁금한 부분 (입시, 학과, 통번역대학원, 캠퍼스 비교 등) 있으면 편하게 물어보세요! 🙌",
        "reasoning_content": "The user is asking for a description/explanation of Hankuk University of Foreign Studies (한국외국어대학교, HUFS) in Korean. The \"ㄱㄱ\" is Korean internet slang meaning \"go go\" or \"let's go\" - essentially asking me to go ahead and explain it. Let me provide a comprehensive overview of HUFS in Korean.\n",
        "tool_calls": null,
        "tool_call_id": null
      },
      "logprobs": null
    }
  ],
  "created": 1794154235,
  "model": "Qwen3.8-Flash-Next-exl3-CMP170HX-64GB",
  "object": "chat.completion",
  "usage": {
    "prompt_tokens": 21,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "prompt_time": 0.11,
    "prompt_tokens_per_sec": 190.91,
    "completion_tokens": 680,
    "completion_tokens_details": {
      "accepted_prediction_tokens": 384,
      "rejected_prediction_tokens": 299
    },
    "completion_time": 6.38,
    "completion_tokens_per_sec": 106.65,
    "total_tokens": 701,
    "total_time": 6.5
  },
  "timings": {
    "cache_n": 0,
    "prompt_n": 21,
    "prompt_ms": 110.0,
    "prompt_per_token_ms": 5.238095238095238,
    "prompt_per_second": 190.90909090909093,
    "predicted_n": 680,
    "predicted_ms": 6380.0,
    "predicted_per_token_ms": 9.382352941176471,
    "predicted_per_second": 106.58307210031349,
    "draft_n": 683,
    "draft_n_accepted": 384
  }
}
```
