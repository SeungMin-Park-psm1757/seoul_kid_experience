# 서울 OpenAPI 연결 진단 보고서

진단 시각: 2026-05-13T11:43:31

본 보고서는 API 키 값을 출력하거나 저장하지 않는다. 성공한 서비스명만 이후 live data pipeline에서 사용한다.

## 요약

- 성공한 공공서비스예약 서비스명: ListPublicReservationCulture, ListPublicReservationEducation, ListPublicReservationSport, ListPublicReservationInstitution
- 성공한 문화행사 서비스명: culturalEventInfo
- 서비스 레지스트리: `data/cache/api_service_registry.json`

실패한 후보 서비스명은 진단 목적의 기록이다. live data pipeline은 서비스 레지스트리에 저장된 성공 서비스명만 사용하므로, 아래 실패가 곧 앱 실행 오류를 의미하지는 않는다.

## 서비스별 진단 결과

| 그룹 | 서비스명 | 결과 | 루트 키 | 샘플 row 수 | RESULT 코드 | 메시지 | 대표 필드 |
|---|---|---|---|---:|---|---|---|
| public_reservation | `ListPublicReservation` | 실패 | `` | 0 | `` | 서버 오류입니다. / 지속적으로 발생시 열린 데이터 광장으로 문의(Q&A) 바랍니다. |  |
| public_reservation | `ListPublicReservationDetail` | 실패 | `` | 0 | `` | 필수 값이 누락되어 있습니다. / 요청인자를 참고 하십시오. |  |
| public_reservation | `ListPublicReservationCulture` | 성공 | `ListPublicReservationCulture` | 5 | `INFO-000` | 정상 처리되었습니다 | GUBUN, SVCID, MAXCLASSNM, MINCLASSNM, SVCSTATNM, SVCNM, PAYATNM, PLACENM, USETGTINFO, SVCURL, X, Y |
| public_reservation | `ListPublicReservationEducation` | 성공 | `ListPublicReservationEducation` | 5 | `INFO-000` | 정상 처리되었습니다 | GUBUN, SVCID, MAXCLASSNM, MINCLASSNM, SVCSTATNM, SVCNM, PAYATNM, PLACENM, USETGTINFO, SVCURL, X, Y |
| public_reservation | `ListPublicReservationSport` | 성공 | `ListPublicReservationSport` | 5 | `INFO-000` | 정상 처리되었습니다 | GUBUN, SVCID, MAXCLASSNM, MINCLASSNM, SVCSTATNM, SVCNM, PAYATNM, PLACENM, USETGTINFO, SVCURL, X, Y |
| public_reservation | `ListPublicReservationInstitution` | 성공 | `ListPublicReservationInstitution` | 5 | `INFO-000` | 정상 처리되었습니다 | GUBUN, SVCID, MAXCLASSNM, MINCLASSNM, SVCSTATNM, SVCNM, PAYATNM, PLACENM, USETGTINFO, SVCURL, X, Y |
| public_reservation | `ListPublicReservationAll` | 실패 | `` | 0 | `` | 서버 오류입니다. / 지속적으로 발생시 열린 데이터 광장으로 문의(Q&A) 바랍니다. |  |
| culture_event | `culturalEventInfo` | 성공 | `culturalEventInfo` | 5 | `INFO-000` | 정상 처리되었습니다 | CODENAME, GUNAME, TITLE, DATE, PLACE, ORG_NAME, USE_TRGT, USE_FEE, INQUIRY, PLAYER, PROGRAM, ETC_DESC |

## 사용 원칙

- 서울 OpenAPI는 한 번에 최대 1,000건씩 호출하고, 1,000건 초과 데이터는 `1~1000`, `1001~2000` 방식으로 나누어 호출한다.
- 공공서비스예약 데이터는 SVCID가 있으면 `https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={SVCID}` 형식의 공식 예약 상세 URL로 연결한다.
- 문화행사 데이터는 예약상태가 명확하지 않을 수 있으므로 공식 출처 링크 확인 필요 또는 참여 가능성으로 표시한다.
- 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 한다.
