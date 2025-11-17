# ELK Stack (Elasticsearch, Logstash, Kibana) 로그 파이프라인 리서치

## 개요

본 문서는 ShopFDS 프로덕션 환경에서 중앙 집중식 로깅 및 모니터링을 위한 ELK Stack (Elasticsearch, Logstash, Kibana) 구축 방안을 리서치한 결과입니다.

**리서치 날짜**: 2025-11-17
**대상 서비스**: 이커머스 백엔드, FDS 서비스, ML 서비스, Admin Dashboard

---

## Decision: ELK Stack with Filebeat, ILM, and Hot-Warm-Cold Architecture

### 선택 이유 (Rationale)

1. **오픈소스 기반 유연성**
   - 완전한 오픈소스 스택으로 커스터마이징 가능성 높음
   - 벤더 종속성(Lock-in) 없음
   - 활발한 커뮤니티 지원 및 방대한 문서

2. **FastAPI 로그 통합 용이성**
   - JSON 형식 로그 네이티브 지원
   - Python 비동기 로깅 라이브러리 풍부 (python-logstash, logstash-async)
   - FastAPI 미들웨어와 원활한 통합

3. **FDS 특화 기능**
   - 실시간 사기 탐지 메트릭 시각화 (차단율, 오탐률, 위험 점수 분포)
   - 그래프 분석 기능으로 사용자 행동 패턴 탐지
   - Machine Learning 이상 탐지 (X-Pack ML) 활용 가능

4. **비용 효율성**
   - 초기 비용: $0 (자체 호스팅 시)
   - Elastic Cloud 비용: ~$50-200/월 (5GB 데이터, 1개 노드 기준)
   - Splunk/Datadog 대비 50-70% 비용 절감

5. **확장성 및 성능**
   - 수평 확장 용이 (샤드 기반 분산 아키텍처)
   - 대용량 로그 처리 가능 (일 1TB+ 인덱싱)
   - Hot-Warm-Cold 아키텍처로 스토리지 비용 최적화

---

## Alternatives Considered

### 1. Splunk Enterprise

**장점**:
- 엔터프라이즈급 기능 (강력한 알림, 상관관계 분석)
- 직관적인 UI 및 강력한 검색 언어 (SPL)
- 실시간 알림 및 대시보드 성능 우수

**단점**:
- 높은 비용 (인덱싱 볼륨 기반 과금, 일 10GB 기준 ~$3,000/월)
- 스타트업/중소기업에는 과도한 투자
- 데이터 보존 비용 급증 (장기 보관 시)

**결론**: 비용 대비 효율성 낮음. ELK 선택.

---

### 2. Datadog

**장점**:
- 클라우드 네이티브 SaaS (설치/유지보수 불필요)
- APM, 로그, 메트릭 통합 플랫폼
- 자동 스케일링 및 간편한 설정

**단점**:
- 사용량 기반 과금 (호스트당 ~$15/월 + 인덱싱 비용)
- 데이터 보존 비용 누적 (15일 기본, 장기 보관 시 추가 비용)
- 커스터마이징 제한 (SaaS 플랫폼 특성)

**결론**: 초기 스타트업에는 비용 부담. ELK로 자체 구축 후 필요시 마이그레이션 고려.

---

### 3. Grafana Loki

**장점**:
- 경량 로그 집계 시스템 (Elasticsearch 대비 리소스 절약)
- Grafana와 네이티브 통합
- S3/MinIO 백엔드 지원 (저렴한 스토리지)

**단점**:
- 전문 검색 기능 제한 (레이블 기반 쿼리만 지원)
- 복잡한 로그 분석 및 집계 어려움
- FDS 특화 시각화 및 ML 기능 부족

**결론**: 단순 로그 수집에는 적합하나, FDS의 복잡한 분석 요구사항 충족 어려움. ELK 선택.

---

## 1. Logstash 파이프라인 설정

### 1.1 Input 설정

#### Filebeat Input (권장)
```ruby
input {
  beats {
    port => 5044
    ssl => true
    ssl_certificate => "/etc/logstash/certs/logstash.crt"
    ssl_key => "/etc/logstash/certs/logstash.key"
    ssl_verify_mode => "force_peer"
  }
}
```

**선택 이유**:
- Filebeat는 경량 로그 수집기로 서버 부하 최소화
- 네트워크 장애 시 자동 재전송 (백프레셔 지원)
- SSL/TLS 암호화로 전송 중 데이터 보안 강화

#### TCP Input (FastAPI 직접 전송용)
```ruby
input {
  tcp {
    port => 5000
    codec => json
    ssl_enable => true
    ssl_cert => "/etc/logstash/certs/logstash.crt"
    ssl_key => "/etc/logstash/certs/logstash.key"
    ssl_verify => false
  }
}
```

**사용 시나리오**:
- FastAPI 애플리케이션에서 python-logstash 라이브러리로 직접 전송
- 낮은 레이턴시 요구사항 (Filebeat 오버헤드 제거)
- 실시간 로그 스트리밍 필요 시

#### HTTP Input (API 엔드포인트)
```ruby
input {
  http {
    port => 8080
    codec => json
    ssl => true
    ssl_certificate => "/etc/logstash/certs/logstash.crt"
    ssl_key => "/etc/logstash/certs/logstash.key"
  }
}
```

**사용 시나리오**:
- 외부 서비스에서 Webhook으로 로그 전송
- 배치 로그 업로드 (bulk API)

---

### 1.2 Filter 설정

#### JSON 파싱
```ruby
filter {
  # FastAPI JSON 로그 파싱
  json {
    source => "message"
    target => "log"
  }

  # 타임스탬프 파싱 (FastAPI ISO 8601 형식)
  date {
    match => ["log.timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # 서비스 분류
  mutate {
    add_field => {
      "service" => "%{[log][service_name]}"
      "environment" => "%{[log][environment]}"
      "log_level" => "%{[log][level]}"
    }
  }

  # 민감 정보 마스킹 (PCI-DSS 준수)
  mutate {
    gsub => [
      "log.card_number", "\d{12}(\d{4})", "************\1",
      "log.cvv", "\d{3,4}", "***"
    ]
  }
}
```

#### Grok 패턴 (비-JSON 로그용)
```ruby
filter {
  # Nginx 액세스 로그 파싱
  grok {
    match => {
      "message" => "%{IPORHOST:client_ip} - %{USER:ident} \[%{HTTPDATE:timestamp}\] \"%{WORD:method} %{URIPATHPARAM:request} HTTP/%{NUMBER:http_version}\" %{NUMBER:response_code} %{NUMBER:bytes}"
    }
  }

  # FastAPI Uvicorn 로그 (Plain Text)
  grok {
    match => {
      "message" => "%{TIMESTAMP_ISO8601:timestamp} \| %{LOGLEVEL:level} \| %{DATA:logger_name} \| %{GREEDYDATA:log_message}"
    }
  }
}
```

#### FDS 특화 필터
```ruby
filter {
  # FDS 평가 결과 로그 감지
  if [log][fds_evaluation] {
    mutate {
      add_field => {
        "risk_score" => "%{[log][fds_evaluation][risk_score]}"
        "risk_level" => "%{[log][fds_evaluation][risk_level]}"
        "decision" => "%{[log][fds_evaluation][decision]}"
      }
    }

    # High Risk 거래 태그 추가
    if [risk_score] > 80 {
      mutate {
        add_tag => ["high_risk", "requires_review"]
      }
    }

    # 사기 차단 이벤트
    if [decision] == "reject" {
      mutate {
        add_tag => ["fraud_blocked"]
      }
    }
  }
}
```

#### Mutate (데이터 변환)
```ruby
filter {
  # 필드 타입 변환
  mutate {
    convert => {
      "response_time" => "float"
      "status_code" => "integer"
      "user_id" => "string"
    }
  }

  # 불필요한 필드 제거
  mutate {
    remove_field => ["agent", "host", "tags"]
  }

  # 지리적 위치 추가 (GeoIP)
  geoip {
    source => "client_ip"
    target => "geo"
    fields => ["country_name", "city_name", "location"]
  }
}
```

---

### 1.3 Output 설정

#### Elasticsearch 인덱싱
```ruby
output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "shopfds-%{[service]}-%{+YYYY.MM.dd}"
    user => "logstash_internal"
    password => "${LOGSTASH_PASSWORD}"

    # ILM 정책 적용
    ilm_enabled => true
    ilm_rollover_alias => "shopfds"
    ilm_pattern => "{now/d}-000001"
    ilm_policy => "shopfds-logs-policy"

    # 성능 최적화
    manage_template => true
    template_overwrite => true
  }

  # 고위험 거래는 별도 인덱스로 전송
  if "high_risk" in [tags] {
    elasticsearch {
      hosts => ["http://elasticsearch:9200"]
      index => "shopfds-high-risk-%{+YYYY.MM.dd}"
      user => "logstash_internal"
      password => "${LOGSTASH_PASSWORD}"
    }
  }

  # 디버깅용 stdout (개발 환경)
  if [environment] == "development" {
    stdout {
      codec => rubydebug
    }
  }
}
```

---

## 2. Kibana 대시보드 구성

### 2.1 에러율 모니터링 대시보드

**시각화 컴포넌트**:

1. **에러율 타임라인** (Line Chart)
   - X축: 타임스탬프 (5분 간격)
   - Y축: 에러 발생 건수
   - 쿼리: `log_level: ERROR OR log_level: CRITICAL`

2. **에러 유형 분포** (Pie Chart)
   - 쿼리: `log_level: ERROR`
   - Aggregation: `Terms` on `log.exception_type`

3. **에러 발생 서비스** (Horizontal Bar Chart)
   - Y축: 서비스명 (ecommerce, fds, ml-service)
   - X축: 에러 건수

4. **에러 로그 테이블** (Data Table)
   - 컬럼: 타임스탬프, 서비스, 로그 레벨, 메시지, 스택 트레이스
   - 필터: 최근 24시간

**Kibana Lens 쿼리 예시**:
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "log_level": "ERROR" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "errors_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "5m"
      }
    }
  }
}
```

---

### 2.2 API 응답 시간 대시보드

**시각화 컴포넌트**:

1. **평균 응답 시간** (Metric)
   - Aggregation: `Average` on `response_time`
   - 목표: <200ms (녹색), 200-500ms (노란색), >500ms (빨간색)

2. **P95 응답 시간 트렌드** (Area Chart)
   - X축: 타임스탬프
   - Y축: Percentile 95th on `response_time`
   - 목표선: FDS 100ms, 이커머스 200ms

3. **엔드포인트별 응답 시간** (Heat Map)
   - X축: 타임스탬프
   - Y축: API 엔드포인트 (log.endpoint)
   - 색상: 평균 응답 시간

4. **느린 요청 Top 10** (Data Table)
   - 정렬: response_time 내림차순
   - 필터: response_time > 500ms

**Elasticsearch 쿼리 예시**:
```json
{
  "query": {
    "bool": {
      "must": [
        { "exists": { "field": "response_time" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "aggs": {
    "percentiles_response_time": {
      "percentiles": {
        "field": "response_time",
        "percents": [50, 90, 95, 99]
      }
    },
    "by_endpoint": {
      "terms": {
        "field": "log.endpoint.keyword",
        "size": 20
      },
      "aggs": {
        "avg_response_time": {
          "avg": { "field": "response_time" }
        }
      }
    }
  }
}
```

---

### 2.3 트래픽 패턴 대시보드

**시각화 컴포넌트**:

1. **총 요청 수** (Metric)
   - Aggregation: `Count`
   - 이전 시간 대비 증감률 표시

2. **시간대별 트래픽** (Vertical Bar Chart)
   - X축: 시간 (1시간 간격)
   - Y축: 요청 수
   - 색상: 서비스별

3. **HTTP 상태 코드 분포** (Donut Chart)
   - 2xx (녹색), 4xx (노란색), 5xx (빨간색)

4. **지역별 트래픽** (Map Visualization)
   - GeoIP 필드 활용
   - 색상: 요청 수 밀도

---

### 2.4 FDS 차단율 대시보드 (특화)

**시각화 컴포넌트**:

1. **사기 차단율** (Gauge)
   - 계산: `(fraud_blocked / total_transactions) * 100`
   - 색상: >5% (빨간색), 2-5% (노란색), <2% (녹색)

2. **위험 점수 분포** (Histogram)
   - X축: 위험 점수 범위 (0-100)
   - Y축: 거래 건수
   - 색상: Low (녹색), Medium (노란색), High (빨간색)

3. **차단된 거래 타임라인** (Area Chart)
   - X축: 타임스탬프
   - Y축: 차단 건수
   - 필터: `decision: reject`

4. **오탐률 모니터링** (Metric)
   - 계산: 수동 리뷰 후 승인된 거래 / 총 차단 거래
   - 목표: <10%

5. **FDS 평가 시간** (Line Chart)
   - X축: 타임스탬프
   - Y축: P95 평가 시간
   - 목표선: 100ms

**Elasticsearch 쿼리 예시**:
```json
{
  "query": {
    "bool": {
      "must": [
        { "exists": { "field": "fds_evaluation" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "fraud_rate": {
      "filters": {
        "filters": {
          "total": { "match_all": {} },
          "blocked": { "term": { "decision.keyword": "reject" } }
        }
      }
    },
    "risk_score_distribution": {
      "histogram": {
        "field": "risk_score",
        "interval": 10
      }
    },
    "fds_evaluation_time": {
      "percentiles": {
        "field": "fds_evaluation.evaluation_time_ms",
        "percents": [50, 95, 99]
      }
    }
  }
}
```

**Machine Learning 이상 탐지 설정**:
```json
{
  "analysis_config": {
    "detectors": [
      {
        "function": "high_count",
        "by_field_name": "decision.keyword",
        "detector_description": "High fraud block rate anomaly"
      },
      {
        "function": "mean",
        "field_name": "risk_score",
        "detector_description": "Unusual average risk score"
      }
    ],
    "influencers": ["geo.country_name", "log.user_id", "log.endpoint"]
  },
  "data_description": {
    "time_field": "@timestamp"
  }
}
```

**Slack 알림 연동** (Elasticsearch Watcher):
```json
{
  "trigger": {
    "schedule": { "interval": "5m" }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["shopfds-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                { "term": { "decision.keyword": "reject" } },
                { "range": { "@timestamp": { "gte": "now-5m" } } }
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": { "ctx.payload.hits.total.value": { "gt": 100 } }
  },
  "actions": {
    "send_slack": {
      "webhook": {
        "method": "POST",
        "url": "https://hooks.slack.com/services/YOUR_WEBHOOK_URL",
        "body": "Fraud block rate spike detected: {{ctx.payload.hits.total.value}} transactions blocked in the last 5 minutes"
      }
    }
  }
}
```

---

### 2.5 로그 검색 및 필터링

**Kibana Discover 활용**:

1. **전문 검색** (Full-Text Search)
   - KQL 쿼리: `log.message: "Payment failed" AND service: ecommerce`
   - 자동완성 지원

2. **필터 추가**
   - 서비스: `service.keyword`
   - 로그 레벨: `log_level.keyword`
   - 시간 범위: Last 15 minutes, Last 24 hours, Custom range

3. **컨텍스트 검색** (주변 로그 확인)
   - 특정 로그 클릭 → "View surrounding documents"
   - 전후 50개 로그 표시 (트레이싱)

4. **저장된 검색** (Saved Searches)
   - "High Risk Transactions"
   - "Payment Failures"
   - "FDS Evaluation Errors"

---

## 3. Curator 자동 삭제

### 3.1 Curator 설정 파일

**curator.yml** (연결 설정):
```yaml
client:
  hosts:
    - elasticsearch
  port: 9200
  url_prefix:
  use_ssl: True
  certificate:
  client_cert:
  client_key:
  ssl_no_validate: False
  http_auth: elastic:changeme
  timeout: 30
  master_only: False

logging:
  loglevel: INFO
  logfile: /var/log/curator/curator.log
  logformat: default
  blacklist: ['elasticsearch', 'urllib3']
```

**actions.yml** (작업 정의):
```yaml
actions:
  1:
    action: delete_indices
    description: "Delete indices older than 30 days"
    options:
      ignore_empty_list: True
      timeout_override:
      continue_if_exception: False
      disable_action: False
    filters:
      - filtertype: pattern
        kind: prefix
        value: shopfds-
      - filtertype: age
        source: name
        direction: older
        timestring: '%Y.%m.%d'
        unit: days
        unit_count: 30

  2:
    action: delete_indices
    description: "Delete high-risk indices older than 90 days (장기 보관)"
    options:
      ignore_empty_list: True
    filters:
      - filtertype: pattern
        kind: prefix
        value: shopfds-high-risk-
      - filtertype: age
        source: name
        direction: older
        timestring: '%Y.%m.%d'
        unit: days
        unit_count: 90

  3:
    action: forcemerge
    description: "Optimize older indices for storage efficiency"
    options:
      max_num_segments: 1
      delay: 120
      timeout_override: 21600
    filters:
      - filtertype: pattern
        kind: prefix
        value: shopfds-
      - filtertype: age
        source: name
        direction: older
        timestring: '%Y.%m.%d'
        unit: days
        unit_count: 7
```

---

### 3.2 Cron 스케줄링

**Crontab 설정**:
```bash
# 매일 새벽 2시에 30일 이상 지난 인덱스 삭제
0 2 * * * /usr/bin/curator --config /etc/curator/curator.yml /etc/curator/actions.yml >> /var/log/curator/cron.log 2>&1
```

**Docker Compose 통합**:
```yaml
services:
  curator:
    image: untergeek/curator:8.0.8
    container_name: curator
    environment:
      - ELASTICSEARCH_HOST=elasticsearch
      - ELASTICSEARCH_PORT=9200
    volumes:
      - ./curator/curator.yml:/etc/curator/curator.yml:ro
      - ./curator/actions.yml:/etc/curator/actions.yml:ro
      - curator-logs:/var/log/curator
    command: >
      bash -c "echo '0 2 * * * curator --config /etc/curator/curator.yml /etc/curator/actions.yml' | crontab - && crond -f"
    depends_on:
      - elasticsearch
```

---

### 3.3 Snapshot 백업 (옵션)

**Snapshot Repository 생성**:
```bash
# S3 리포지토리 설정 (AWS)
PUT _snapshot/s3_backup
{
  "type": "s3",
  "settings": {
    "bucket": "shopfds-elasticsearch-backups",
    "region": "ap-northeast-2",
    "base_path": "snapshots"
  }
}

# 파일 시스템 리포지토리 (온프레미스)
PUT _snapshot/fs_backup
{
  "type": "fs",
  "settings": {
    "location": "/mnt/elasticsearch/snapshots"
  }
}
```

**Curator Snapshot 작업**:
```yaml
actions:
  4:
    action: snapshot
    description: "Create weekly snapshot before deletion"
    options:
      repository: s3_backup
      name: "shopfds-snapshot-%Y%m%d"
      ignore_unavailable: False
      include_global_state: False
      partial: False
      wait_for_completion: True
      skip_repo_fs_check: False
    filters:
      - filtertype: pattern
        kind: prefix
        value: shopfds-
      - filtertype: age
        source: name
        direction: older
        timestring: '%Y.%m.%d'
        unit: days
        unit_count: 28  # 삭제 2일 전 백업
```

**스냅샷 복원 예시**:
```bash
# 특정 날짜 스냅샷 복원
POST _snapshot/s3_backup/shopfds-snapshot-20251115/_restore
{
  "indices": "shopfds-ecommerce-2025.11.15",
  "ignore_unavailable": true,
  "include_global_state": false
}
```

---

## 4. 인덱스 라이프사이클 관리 (ILM)

### 4.1 Hot-Warm-Cold 아키텍처

**노드 역할 정의**:

| 노드 유형 | 역할 | 하드웨어 스펙 | 데이터 보관 기간 |
|----------|------|--------------|----------------|
| **Hot**  | 활발한 인덱싱 및 검색 | 32GB RAM, NVMe SSD, 8 vCPU | 0-7일 |
| **Warm** | 가끔 검색, 읽기 전용 | 16GB RAM, SATA SSD, 4 vCPU | 7-30일 |
| **Cold** | 드물게 검색, 아카이브 | 8GB RAM, HDD, 2 vCPU | 30-90일 |
| **Frozen** | 거의 미사용, 압축 저장 | 4GB RAM, HDD, 1 vCPU | 90일+ |

**Elasticsearch Node Attributes**:
```yaml
# elasticsearch.yml (Hot Node)
node.name: hot-node-1
node.roles: [ data_hot, ingest, transform ]
node.attr.data: hot

# elasticsearch.yml (Warm Node)
node.name: warm-node-1
node.roles: [ data_warm ]
node.attr.data: warm

# elasticsearch.yml (Cold Node)
node.name: cold-node-1
node.roles: [ data_cold ]
node.attr.data: cold
```

---

### 4.2 ILM 정책 정의

**shopfds-logs-policy**:
```json
PUT _ilm/policy/shopfds-logs-policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "50GB",
            "max_age": "1d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          },
          "allocate": {
            "require": {
              "data": "warm"
            }
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "allocate": {
            "require": {
              "data": "cold"
            }
          },
          "set_priority": {
            "priority": 0
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

**High-Risk 로그 정책** (장기 보관):
```json
PUT _ilm/policy/shopfds-high-risk-policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "30GB",
            "max_age": "7d"
          }
        }
      },
      "warm": {
        "min_age": "30d",
        "actions": {
          "shrink": { "number_of_shards": 1 },
          "forcemerge": { "max_num_segments": 1 },
          "allocate": { "require": { "data": "warm" } }
        }
      },
      "cold": {
        "min_age": "90d",
        "actions": {
          "allocate": { "require": { "data": "cold" } }
        }
      },
      "frozen": {
        "min_age": "180d",
        "actions": {
          "searchable_snapshot": {
            "snapshot_repository": "s3_backup"
          }
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

---

### 4.3 Rollover 정책

**Index Template 생성**:
```json
PUT _index_template/shopfds-logs
{
  "index_patterns": ["shopfds-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "index.lifecycle.name": "shopfds-logs-policy",
      "index.lifecycle.rollover_alias": "shopfds-logs"
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "service": { "type": "keyword" },
        "log_level": { "type": "keyword" },
        "message": { "type": "text" },
        "response_time": { "type": "float" },
        "risk_score": { "type": "integer" },
        "decision": { "type": "keyword" },
        "geo": {
          "properties": {
            "location": { "type": "geo_point" }
          }
        }
      }
    }
  }
}
```

**초기 인덱스 생성**:
```bash
# 첫 번째 인덱스 생성 (Rollover 시작점)
PUT shopfds-logs-000001
{
  "aliases": {
    "shopfds-logs": {
      "is_write_index": true
    }
  }
}
```

**Rollover 조건**:
- **크기 기준**: Primary Shard가 50GB 도달 시
- **시간 기준**: 인덱스 생성 후 1일 경과 시
- **문서 수 기준** (옵션): 1,000만 문서 도달 시

**수동 Rollover 실행**:
```bash
POST shopfds-logs/_rollover
{
  "conditions": {
    "max_age": "1d",
    "max_primary_shard_size": "50GB",
    "max_docs": 10000000
  }
}
```

---

## 5. 성능 최적화

### 5.1 샤드 수 결정

**권장 사항**:
- **인덱스당 Primary Shard 수**: 1-3개 (일별 로그 인덱스 기준)
- **샤드 크기**: 10-50GB (최적: 30GB)
- **노드당 총 샤드 수**: 600개 미만 (30GB Heap 기준, 20 shards/GB)

**계산 예시**:
```
- 일일 로그 생성량: 100GB
- 목표 Primary Shard 크기: 50GB
- Primary Shard 수: 100GB / 50GB = 2개
- Replica 수: 1 (고가용성)
- 총 Shard 수: 2 (Primary) + 2 (Replica) = 4개
```

**동적 샤드 조정** (ILM Shrink):
```json
{
  "warm": {
    "actions": {
      "shrink": {
        "number_of_shards": 1
      }
    }
  }
}
```
→ Warm Phase 진입 시 3개 샤드를 1개로 병합 (저장 공간 및 검색 효율 개선)

---

### 5.2 Refresh Interval 조정

**기본 설정**: 1초 (실시간 검색 우선)
**최적화 설정**: 30초 (인덱싱 성능 우선)

**Index Template에 적용**:
```json
PUT _index_template/shopfds-logs
{
  "template": {
    "settings": {
      "index.refresh_interval": "30s"
    }
  }
}
```

**동적 변경** (특정 인덱스):
```bash
PUT shopfds-logs-000001/_settings
{
  "index.refresh_interval": "30s"
}
```

**Bulk 인덱싱 시 비활성화** (최대 성능):
```bash
# Refresh 비활성화
PUT shopfds-logs-000001/_settings
{
  "index.refresh_interval": "-1"
}

# Bulk 인덱싱 실행
POST _bulk
...

# Refresh 재활성화
PUT shopfds-logs-000001/_settings
{
  "index.refresh_interval": "30s"
}

# 수동 Refresh
POST shopfds-logs-000001/_refresh
```

**성능 영향**:
- 1s → 30s 변경 시: 인덱싱 처리량 30-50% 증가
- Refresh 비활성화 시: 인덱싱 처리량 100-200% 증가 (단, 검색 불가)

---

### 5.3 Bulk Indexing

**Logstash Bulk 설정**:
```ruby
output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "shopfds-%{[service]}-%{+YYYY.MM.dd}"

    # Bulk 최적화
    flush_size => 5000       # 5000개 문서 단위로 전송
    idle_flush_time => 5     # 최대 5초 대기
    workers => 4             # 4개 병렬 워커
  }
}
```

**Python Bulk API 사용** (FastAPI 직접 인덱싱):
```python
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch(["http://elasticsearch:9200"])

actions = [
    {
        "_index": "shopfds-logs",
        "_source": {
            "timestamp": "2025-11-17T12:00:00Z",
            "service": "ecommerce",
            "message": "Payment processed successfully"
        }
    }
    for _ in range(10000)
]

# Bulk 인덱싱
helpers.bulk(es, actions, chunk_size=5000, request_timeout=60)
```

**최적 Bulk 크기**:
- **권장**: 5-15MB per request
- **문서 수**: 1,000-5,000개 (문서 크기에 따라 다름)
- **실험 방법**: 벤치마크 테스트로 최적값 찾기

**성능 벤치마크**:
```bash
# Elasticsearch Bulk Benchmark
curl -X POST "http://elasticsearch:9200/_bulk?pretty" \
  -H 'Content-Type: application/json' \
  --data-binary "@bulk_data.json"

# esrally 사용 (공식 벤치마크 도구)
esrally race --track=http_logs --target-hosts=localhost:9200
```

---

### 5.4 추가 최적화 팁

#### 1. Translog Durability
```json
{
  "index.translog.durability": "async",
  "index.translog.sync_interval": "30s"
}
```
→ fsync 빈도 감소로 인덱싱 성능 향상 (데이터 손실 위험 증가)

#### 2. Index Buffer Size
```yaml
# elasticsearch.yml
indices.memory.index_buffer_size: 20%
```
→ Heap의 20%를 인덱싱 버퍼로 할당 (기본: 10%)

#### 3. Disable Swapping
```yaml
# elasticsearch.yml
bootstrap.memory_lock: true
```
→ Swap 방지로 성능 저하 예방

#### 4. OS 캐시 최적화
```bash
# 파일 시스템 캐시 크기 증가
echo 'vm.swappiness = 1' >> /etc/sysctl.conf
echo 'vm.max_map_count = 262144' >> /etc/sysctl.conf
sysctl -p
```

#### 5. 불필요한 _source 필드 비활성화 (메트릭 인덱스)
```json
{
  "mappings": {
    "_source": {
      "enabled": false
    }
  }
}
```
→ 저장 공간 절약 (단, Reindex/Update 불가)

---

## Implementation Notes

### 1. 프로덕션 배포 체크리스트

#### [PHASE 1] 인프라 준비
- [ ] Elasticsearch 클러스터 구성 (최소 3개 노드)
- [ ] Hot/Warm/Cold 노드 역할 할당
- [ ] 디스크 용량 계획 (일일 로그량 x 보관 기간 x 1.5 안전 계수)
- [ ] Elasticsearch Heap 설정 (물리 메모리의 50%, 최대 31GB)
- [ ] 네트워크 방화벽 규칙 (9200, 9300 포트 오픈)

#### [PHASE 2] Logstash 설정
- [ ] Filebeat 설치 (모든 서버)
- [ ] Logstash 파이프라인 작성 (input, filter, output)
- [ ] Grok 패턴 테스트 (Kibana Dev Tools)
- [ ] 민감 정보 마스킹 필터 추가
- [ ] SSL/TLS 인증서 생성 및 배포

#### [PHASE 3] Kibana 대시보드
- [ ] 인덱스 패턴 생성 (shopfds-*)
- [ ] 에러율 대시보드 구성
- [ ] API 응답 시간 대시보드 구성
- [ ] FDS 차단율 대시보드 구성
- [ ] Watcher 알림 설정 (Slack/Email)

#### [PHASE 4] ILM 및 Curator
- [ ] ILM 정책 생성 및 적용
- [ ] Index Template 생성
- [ ] 초기 Rollover 인덱스 생성
- [ ] Curator 설정 파일 작성
- [ ] Cron 스케줄 등록
- [ ] Snapshot Repository 생성 (S3 또는 NFS)

#### [PHASE 5] 성능 테스트
- [ ] Bulk 인덱싱 벤치마크 (esrally)
- [ ] Refresh Interval 튜닝
- [ ] 샤드 수 최적화
- [ ] 쿼리 성능 테스트
- [ ] 부하 테스트 (JMeter 또는 Locust)

#### [PHASE 6] 모니터링 및 알림
- [ ] Elasticsearch 클러스터 상태 모니터링
- [ ] 디스크 사용률 알림 (80% 임계값)
- [ ] Heap 사용률 모니터링 (75% 임계값)
- [ ] 인덱싱 지연 모니터링
- [ ] Kibana 대시보드 접근 권한 설정

---

### 2. 주의사항 및 트러블슈팅

#### A. Windows 환경 개발 시
- **cp949 인코딩 문제**: Logstash Grok 패턴에 이모지 사용 금지
  ```ruby
  # WRONG
  mutate { add_field => { "status" => "✅ Success" } }

  # CORRECT
  mutate { add_field => { "status" => "[OK] Success" } }
  ```

#### B. Elasticsearch OOM (Out of Memory)
- **증상**: 클러스터 재시작, 노드 이탈
- **원인**: Heap 부족, 너무 많은 샤드, 과도한 집계 쿼리
- **해결**:
  - Heap 크기 증가 (최대 31GB)
  - 샤드 수 줄이기 (ILM Shrink 활용)
  - 집계 쿼리 최적화 (terms aggregation size 제한)

#### C. Slow Indexing
- **증상**: 로그 인덱싱 지연, 큐 쌓임
- **원인**: Refresh Interval 너무 짧음, 샤드 크기 과대, Disk I/O 병목
- **해결**:
  - Refresh Interval 30s로 증가
  - 샤드 수 증가 (노드 수와 맞춤)
  - SSD 사용 (Hot Node는 NVMe 권장)

#### D. Kibana 대시보드 느림
- **증상**: 대시보드 로딩 10초 이상
- **원인**: 너무 넓은 시간 범위, 비효율적인 쿼리, 너무 많은 시각화
- **해결**:
  - 시간 범위 좁히기 (Last 24h → Last 1h)
  - 쿼리 캐싱 활성화
  - 시각화 개수 줄이기 (페이지당 10개 이하)

#### E. 디스크 가득 참
- **증상**: Elasticsearch Read-Only 모드 전환
- **원인**: Curator 미실행, ILM 정책 미적용
- **해결**:
  - 수동 인덱스 삭제: `DELETE /shopfds-*-2025.10.*`
  - Disk Watermark 조정: `cluster.routing.allocation.disk.watermark.low: 90%`
  - 추가 디스크 증설

---

### 3. 보안 강화

#### A. Elasticsearch 인증/인가
```yaml
# elasticsearch.yml
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true
```

**사용자 생성**:
```bash
# Logstash 전용 사용자
POST _security/user/logstash_internal
{
  "password": "StrongPassword123!",
  "roles": ["logstash_writer"],
  "full_name": "Logstash Internal User"
}

# Kibana 읽기 전용 사용자
POST _security/user/analyst
{
  "password": "AnalystPassword123!",
  "roles": ["kibana_user", "viewer"],
  "full_name": "Security Analyst"
}
```

#### B. Kibana 접근 제어
- **RBAC**: Role-Based Access Control 활성화
- **Space 분리**: 이커머스팀, 보안팀, 개발팀별 Space 생성
- **IP Whitelisting**: Nginx에서 IP 필터링

#### C. 로그 민감 정보 보호
- **PCI-DSS 준수**: 카드번호, CVV 자동 마스킹 (Logstash Filter)
- **GDPR 준수**: 개인정보 암호화 또는 익명화
- **감사 로그**: Elasticsearch Audit Log 활성화

---

### 4. 비용 최적화

#### A. 스토리지 비용 절감
- **Cold/Frozen Phase 활용**: HDD 사용으로 70% 비용 절감
- **Snapshot to S3**: Elasticsearch → S3 Glacier (90% 절감)
- **Forcemerge**: 세그먼트 병합으로 디스크 20% 절약

#### B. 컴퓨팅 비용 절감
- **Auto Scaling**: 트래픽에 따라 노드 수 동적 조정
- **Spot Instance**: AWS Spot Instance로 50% 절감 (Warm/Cold Node)
- **Serverless 고려**: Elastic Cloud Serverless (소규모 팀)

#### C. 네트워크 비용 절감
- **Region 일치**: Elasticsearch와 Logstash 동일 Region 배치
- **Compression**: gzip 압축으로 전송량 60% 감소
- **로컬 캐싱**: Filebeat에서 로컬 버퍼링

---

### 5. FastAPI 통합 코드 예시

#### Python Logstash Handler
```python
# services/ecommerce/backend/src/utils/logging_config.py
import logging
import logstash
from pythonjsonlogger import jsonlogger

def setup_elk_logging(service_name: str):
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    # Logstash Handler (TCP)
    logstash_handler = logstash.TCPLogstashHandler(
        host='logstash',
        port=5000,
        version=1
    )
    logger.addHandler(logstash_handler)

    # JSON Formatter (Filebeat용)
    json_handler = logging.FileHandler('/var/log/shopfds/app.log')
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    json_handler.setFormatter(formatter)
    logger.addHandler(json_handler)

    return logger

# 사용 예시
logger = setup_elk_logging("ecommerce")
logger.info("Order created", extra={
    "order_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user123",
    "amount": 50000,
    "fds_evaluation": {
        "risk_score": 25,
        "decision": "approve"
    }
})
```

#### Filebeat 설정 (Docker)
```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/shopfds/*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      service: ecommerce
      environment: production

output.logstash:
  hosts: ["logstash:5044"]
  ssl.enabled: true
  ssl.certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
  ssl.certificate: "/etc/filebeat/certs/filebeat.crt"
  ssl.key: "/etc/filebeat/certs/filebeat.key"

processors:
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
```

---

## 결론

**ELK Stack 선택 요약**:
- **비용**: Splunk/Datadog 대비 50-70% 절감
- **유연성**: 오픈소스 기반 완전한 커스터마이징
- **확장성**: Hot-Warm-Cold 아키텍처로 무제한 확장
- **FDS 특화**: 사기 탐지 대시보드, ML 이상 탐지, 실시간 알림

**핵심 구현 사항**:
1. Logstash 파이프라인: Filebeat → JSON 파싱 → Elasticsearch 인덱싱
2. Kibana 대시보드: 에러율, API 응답 시간, FDS 차단율 시각화
3. Curator: 30일 이상 인덱스 자동 삭제, S3 백업
4. ILM: Hot(7일) → Warm(30일) → Cold(90일) → Delete
5. 성능 최적화: 3개 샤드, 30s Refresh Interval, Bulk Indexing

**다음 단계**:
- 프로토타입 환경 구축 (Docker Compose)
- 성능 벤치마크 (esrally)
- 프로덕션 배포 (Kubernetes)
- 비용 모니터링 및 최적화

---

## 참고 자료

- [Elastic Official Documentation](https://www.elastic.co/guide/index.html)
- [Logstash Pipeline Configuration](https://www.elastic.co/guide/en/logstash/current/configuration.html)
- [Kibana Dashboard Examples](https://www.elastic.co/kibana/features)
- [Elasticsearch ILM Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-lifecycle-management.html)
- [Curator Documentation](https://www.elastic.co/guide/en/elasticsearch/client/curator/current/index.html)
- [FastAPI Elasticsearch Middleware](https://pypi.org/project/fastapi-elasticsearch-middleware/)
- [Elasticsearch Performance Tuning](https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-indexing-speed.html)
