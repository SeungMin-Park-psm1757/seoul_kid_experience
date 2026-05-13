# Codex 프롬프트 01 — 데이터 파이프라인 우선 구현

이 프로젝트는 웹서비스가 아니라 공공데이터 기반 시각화 결과물이다. 먼저 데이터 파이프라인과 핵심 시각화를 만든다.

작업:
1. `src.build_all --sample`이 정상 실행되는지 확인하라.
2. 샘플 데이터가 생성되지 않으면 `src/sample_data.py`를 보완하라.
3. `data/processed/unified_programs.csv`, `district_age_metrics.csv`, `weekly_choice_metrics.csv`를 생성하라.
4. `outputs/figures/`에 5개 핵심 시각화를 저장하라.
5. Streamlit 앱은 생성된 시각화를 읽어 보여주는 수준으로만 유지하라.

금지:
- 로그인
- 예약 자동화
- 실시간 크롤링
- 알림/회원관리
- 서비스 기능 고도화

우선 결과물이 돌아가게 하라.
