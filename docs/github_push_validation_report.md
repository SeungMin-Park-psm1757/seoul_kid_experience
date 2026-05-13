# GitHub 푸시 검증 보고서

검증일: 2026-05-13

## 검증 대상

- 원격 저장소: `https://github.com/SeungMin-Park-psm1757/seoul_kid_experience.git`
- 브랜치: `main`
- 원격 HEAD: `538c058ebd6df9ffb3ddc8dc22332d5f1f69f4b9`
- 로컬 커밋: `538c058 Initial Seoul kid experience curator MVP`

## 검증 결과

| 항목 | 결과 | 확인 내용 |
|---|---|---|
| 원격 브랜치 반영 | 통과 | `origin/main`과 로컬 `main`이 같은 커밋을 가리킨다. |
| 기본 HEAD 확인 | 통과 | 원격 `HEAD`가 `main`의 최신 커밋과 일치한다. |
| 민감 파일 제외 | 통과 | `.env`, `data/cache/`, `data/snapshots/`, 로그 파일은 커밋 대상에서 제외되어 있다. |
| API 키 노출 검사 | 통과 | `.env`의 실제 키 값이 추적 파일에 포함되지 않았다. |
| Python 컴파일 | 통과 | `python tools/compile_check.py`로 앱과 주요 모듈 컴파일을 확인했다. |
| 자동 테스트 | 통과 | `python -m pytest -q` 결과 41개 테스트가 통과했다. |

## 보완 사항

- Windows PowerShell에서는 `python -m py_compile app.py src/*.py src/api/*.py` 형태의 glob 명령이 그대로 전달되어 실패할 수 있다.
- 이를 방지하기 위해 `tools/compile_check.py`를 추가하고 검증 문서의 컴파일 명령을 `python tools/compile_check.py`로 정리했다.

## 주의

본 저장소에는 API 키를 포함하지 않는다. 실제 실행 시에는 로컬 `.env`에 키를 설정하고, 공식 예약 가능 여부와 회차별 잔여석은 각 공식 예약/출처 링크에서 최종 확인해야 한다.
