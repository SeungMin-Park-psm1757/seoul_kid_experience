# 시각화 완성 후 PPT 제작 계획

PPT는 지금 바로 완성하지 않는다. 실제 데이터 기반 시각화 결과가 나온 뒤 작성한다.

## PPT 제작 전 필요한 산출물

1. `outputs/figures/01_empty_weekend_calendar.png`
2. `outputs/figures/02_planb_tilemap.png`
3. `outputs/figures/03_age_blindspot_heatmap.png`
4. `outputs/figures/04_choice_planb_matrix.png`
5. `outputs/figures/05_barrier_decomposition.png`
6. `docs/data_audit.md`
7. `docs/metrics_result_summary.md`
8. `docs/visualization_interpretation.md`

## 20장 PPT 골격

1. 표지
2. 문제 제기: 서울에는 체험이 있지만 고르기 어렵다
3. 문제를 바꾸어 묻기: 누가 실제로 선택할 수 있는가
4. 기존 정보 경로의 한계
5. 작품 목표: 선택가능도와 플랜B 격차 시각화
6. 데이터 구성
7. 데이터 처리 흐름
8. 선택가능도 지수 정의
9. 플랜B 충분도 지수 정의
10. 빈 주말 캘린더 결과
11. 플랜B 충분도 지도 결과
12. 연령별 블라인드 스팟 결과
13. 선택가능도 × 플랜B 2×2 유형화
14. 이용장벽 분해 결과
15. 인터랙티브 시각화 구조
16. 부모 관점 화면
17. 서울시 정책 관점 화면
18. 정책 제안
19. 한계와 보완계획
20. 결론

## NotebookLM 투입 시점

위 산출물들이 생성된 뒤 NotebookLM에 다음 자료를 넣는다.

- 데이터 출처표
- 지표 정의서
- 생성된 시각화 이미지
- 지표 결과 요약표
- 레드팀 체크리스트

그 후 PPT 초안을 생성하고, 페이지별 수정 프롬프트로 보완한다.
