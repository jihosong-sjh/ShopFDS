"""
003-advanced-fds: Add advanced FDS models

Revision ID: 003_advanced_fds
Revises: 9afda0dcb7d2
Create Date: 2025-11-18 00:00:00.000000

13개 신규 엔티티 추가:
- DeviceFingerprint: 디바이스 핑거프린트
- BehaviorPattern: 행동 패턴
- NetworkAnalysis: 네트워크 분석
- FraudRule: 사기 탐지 룰
- RuleExecution: 룰 실행 결과
- MLModelVersion: ML 모델 버전
- EnsemblePrediction: 앙상블 예측
- FeatureImportance: Feature 중요도
- XAIExplanation: XAI 설명
- DataDriftLog: 데이터 드리프트 로그
- RetrainingJob: 재학습 작업
- ExternalServiceLog: 외부 서비스 로그
- BlacklistEntry: 블랙리스트
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_advanced_fds'
down_revision = '9afda0dcb7d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. DeviceFingerprint
    op.create_table(
        'device_fingerprints',
        sa.Column('device_id', sa.String(length=64), nullable=False, comment='SHA-256 해시'),
        sa.Column('canvas_hash', sa.String(length=64), nullable=False, comment='Canvas API 해시'),
        sa.Column('webgl_hash', sa.String(length=64), nullable=False, comment='WebGL API 해시'),
        sa.Column('audio_hash', sa.String(length=64), nullable=False, comment='Audio API 해시'),
        sa.Column('cpu_cores', sa.Integer(), nullable=False, comment='CPU 코어 수'),
        sa.Column('memory_size', sa.Integer(), nullable=False, comment='메모리 크기 (MB)'),
        sa.Column('screen_resolution', sa.String(length=20), nullable=False, comment='화면 해상도'),
        sa.Column('timezone', sa.String(length=50), nullable=False, comment='타임존'),
        sa.Column('language', sa.String(length=10), nullable=False, comment='언어'),
        sa.Column('user_agent', sa.Text(), nullable=False, comment='User-Agent'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='마지막 활동 일시'),
        sa.Column('blacklisted', sa.Boolean(), nullable=False, server_default='false', comment='블랙리스트 여부'),
        sa.Column('blacklist_reason', sa.Text(), nullable=True, comment='블랙리스트 사유'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정 일시'),
        sa.PrimaryKeyConstraint('device_id', name='pk_device_fingerprints')
    )
    op.create_index('idx_device_fingerprints_created_at', 'device_fingerprints', ['created_at'])
    op.create_index('idx_device_fingerprints_blacklisted', 'device_fingerprints', ['blacklisted'])

    # 2. BehaviorPattern
    op.create_table(
        'behavior_patterns',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='세션 ID'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='사용자 ID'),
        sa.Column('mouse_movements', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='마우스 움직임 데이터'),
        sa.Column('keyboard_events', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='키보드 이벤트'),
        sa.Column('clickstream', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='클릭스트림'),
        sa.Column('bot_score', sa.Integer(), nullable=False, server_default='0', comment='봇 확률'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.PrimaryKeyConstraint('session_id', name='pk_behavior_patterns')
    )
    op.create_index('idx_behavior_patterns_user_id', 'behavior_patterns', ['user_id'])
    op.create_index('idx_behavior_patterns_created_at', 'behavior_patterns', ['created_at'])

    # 3. NetworkAnalysis
    op.create_table(
        'network_analysis',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, comment='거래 ID'),
        sa.Column('ip_address', postgresql.INET(), nullable=False, comment='IP 주소'),
        sa.Column('geoip_country', sa.String(length=2), nullable=True, comment='GeoIP 국가 코드'),
        sa.Column('geoip_city', sa.String(length=50), nullable=True, comment='GeoIP 도시'),
        sa.Column('asn', sa.Integer(), nullable=True, comment='AS 번호'),
        sa.Column('asn_organization', sa.String(length=255), nullable=True, comment='AS 조직명'),
        sa.Column('is_tor', sa.Boolean(), nullable=False, server_default='false', comment='TOR 사용 여부'),
        sa.Column('is_vpn', sa.Boolean(), nullable=False, server_default='false', comment='VPN 사용 여부'),
        sa.Column('is_proxy', sa.Boolean(), nullable=False, server_default='false', comment='프록시 사용 여부'),
        sa.Column('dns_ptr_record', sa.String(length=255), nullable=True, comment='DNS PTR 레코드'),
        sa.Column('country_mismatch', sa.Boolean(), nullable=False, server_default='false', comment='국가 불일치 여부'),
        sa.Column('risk_score', sa.Integer(), nullable=False, server_default='0', comment='위험 점수'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.PrimaryKeyConstraint('transaction_id', name='pk_network_analysis')
    )
    op.create_index('idx_network_analysis_ip_address', 'network_analysis', ['ip_address'])
    op.create_index('idx_network_analysis_created_at', 'network_analysis', ['created_at'])

    # 4. FraudRule
    # Create rule_category ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rule_category')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE rule_category AS ENUM ('payment', 'account', 'shipping')")
    op.create_table(
        'fraud_rules',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='룰 ID'),
        sa.Column('rule_name', sa.String(length=255), nullable=False, comment='룰 이름'),
        sa.Column('rule_category', postgresql.ENUM('payment', 'account', 'shipping', name='rule_category', create_type=False), nullable=False, comment='룰 카테고리'),
        sa.Column('rule_description', sa.Text(), nullable=True, comment='룰 설명'),
        sa.Column('rule_logic', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='룰 실행 로직'),
        sa.Column('risk_score', sa.Integer(), nullable=False, comment='점수'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='활성화 여부'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='우선순위'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정 일시'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='생성자 ID'),
        sa.PrimaryKeyConstraint('rule_id', name='pk_fraud_rules')
    )
    op.create_index('idx_fraud_rules_category', 'fraud_rules', ['rule_category'])
    op.create_index('idx_fraud_rules_is_active', 'fraud_rules', ['is_active'])
    op.create_index('idx_fraud_rules_priority', 'fraud_rules', ['priority'])

    # 5. RuleExecution
    op.create_table(
        'rule_executions',
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='실행 ID'),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, comment='거래 ID'),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False, comment='룰 ID'),
        sa.Column('matched', sa.Boolean(), nullable=False, comment='매칭 여부'),
        sa.Column('triggered_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='트리거 일시'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='매칭 상세 정보'),
        sa.PrimaryKeyConstraint('execution_id', name='pk_rule_executions')
    )
    op.create_index('idx_rule_executions_transaction_id', 'rule_executions', ['transaction_id'])
    op.create_index('idx_rule_executions_rule_id', 'rule_executions', ['rule_id'])
    op.create_index('idx_rule_executions_triggered_at', 'rule_executions', ['triggered_at'])

    # 6. MLModelVersion
    # Create model_name ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'model_name')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE model_name AS ENUM ('random_forest', 'xgboost', 'autoencoder', 'lstm')")
    op.create_table(
        'ml_model_versions',
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='버전 ID'),
        sa.Column('model_name', postgresql.ENUM('random_forest', 'xgboost', 'autoencoder', 'lstm', name='model_name', create_type=False), nullable=False, comment='모델 이름'),
        sa.Column('model_type', sa.String(length=50), nullable=True, comment='모델 타입'),
        sa.Column('version_number', sa.String(length=20), nullable=False, comment='버전 번호'),
        sa.Column('trained_at', sa.DateTime(), nullable=False, comment='학습 일시'),
        sa.Column('accuracy', sa.Float(), nullable=True, comment='정확도'),
        sa.Column('precision', sa.Float(), nullable=True, comment='정밀도'),
        sa.Column('recall', sa.Float(), nullable=True, comment='재현율'),
        sa.Column('f1_score', sa.Float(), nullable=True, comment='F1 Score'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false', comment='활성화 여부'),
        sa.Column('model_path', sa.String(length=255), nullable=False, comment='모델 파일 경로'),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='하이퍼파라미터'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.PrimaryKeyConstraint('version_id', name='pk_ml_model_versions'),
        sa.UniqueConstraint('model_name', 'version_number', name='uq_ml_model_name_version')
    )
    op.create_index('idx_ml_model_versions_is_active', 'ml_model_versions', ['is_active'])
    op.create_index('idx_ml_model_versions_trained_at', 'ml_model_versions', ['trained_at'])

    # 7. EnsemblePrediction
    # Create prediction_decision ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'prediction_decision')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE prediction_decision AS ENUM ('allow', 'block', 'review')")
    op.create_table(
        'ensemble_predictions',
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='예측 ID'),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, comment='거래 ID'),
        sa.Column('rf_score', sa.Float(), nullable=True, comment='Random Forest 예측'),
        sa.Column('xgb_score', sa.Float(), nullable=True, comment='XGBoost 예측'),
        sa.Column('autoencoder_score', sa.Float(), nullable=True, comment='Autoencoder 예측'),
        sa.Column('lstm_score', sa.Float(), nullable=True, comment='LSTM 예측'),
        sa.Column('ensemble_score', sa.Float(), nullable=False, comment='가중 평균'),
        sa.Column('final_decision', postgresql.ENUM('allow', 'block', 'review', name='prediction_decision', create_type=False), nullable=False, comment='최종 결정'),
        sa.Column('predicted_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='예측 일시'),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=True, comment='모델 버전 ID'),
        sa.PrimaryKeyConstraint('prediction_id', name='pk_ensemble_predictions')
    )
    op.create_index('idx_ensemble_predictions_transaction_id', 'ensemble_predictions', ['transaction_id'])
    op.create_index('idx_ensemble_predictions_predicted_at', 'ensemble_predictions', ['predicted_at'])

    # 8. FeatureImportance
    op.create_table(
        'feature_importances',
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='분석 ID'),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=False, comment='모델 버전 ID'),
        sa.Column('feature_name', sa.String(length=255), nullable=False, comment='Feature 이름'),
        sa.Column('importance_score', sa.Float(), nullable=False, comment='중요도 점수'),
        sa.Column('rank', sa.Integer(), nullable=False, comment='순위'),
        sa.Column('analyzed_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='분석 일시'),
        sa.PrimaryKeyConstraint('analysis_id', name='pk_feature_importances')
    )
    op.create_index('idx_feature_importances_model_version_id', 'feature_importances', ['model_version_id'])
    op.create_index('idx_feature_importances_rank', 'feature_importances', ['rank'])

    # 9. XAIExplanation
    op.create_table(
        'xai_explanations',
        sa.Column('explanation_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='설명 ID'),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, comment='거래 ID'),
        sa.Column('shap_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='SHAP 값'),
        sa.Column('lime_explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='LIME 설명'),
        sa.Column('top_risk_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='상위 위험 요인'),
        sa.Column('explanation_time_ms', sa.Integer(), nullable=True, comment='계산 시간'),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.PrimaryKeyConstraint('explanation_id', name='pk_xai_explanations')
    )
    op.create_index('idx_xai_explanations_transaction_id', 'xai_explanations', ['transaction_id'])
    op.create_index('idx_xai_explanations_generated_at', 'xai_explanations', ['generated_at'])

    # 10. DataDriftLog
    op.create_table(
        'data_drift_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='로그 ID'),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='감지 일시'),
        sa.Column('metric_name', sa.String(length=255), nullable=False, comment='메트릭 이름'),
        sa.Column('baseline_value', sa.Float(), nullable=False, comment='기준값'),
        sa.Column('current_value', sa.Float(), nullable=False, comment='현재값'),
        sa.Column('drift_percentage', sa.Float(), nullable=False, comment='변화율'),
        sa.Column('alert_triggered', sa.Boolean(), nullable=False, server_default='false', comment='알림 트리거 여부'),
        sa.Column('alert_message', sa.Text(), nullable=True, comment='알림 메시지'),
        sa.PrimaryKeyConstraint('log_id', name='pk_data_drift_logs')
    )
    op.create_index('idx_data_drift_logs_detected_at', 'data_drift_logs', ['detected_at'])
    op.create_index('idx_data_drift_logs_alert_triggered', 'data_drift_logs', ['alert_triggered'])

    # 11. RetrainingJob
    # Create retrain_trigger_type ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'retrain_trigger_type')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE retrain_trigger_type AS ENUM ('auto', 'manual')")
    # Create retrain_status ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'retrain_status')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE retrain_status AS ENUM ('pending', 'running', 'completed', 'failed')")
    op.create_table(
        'retraining_jobs',
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='작업 ID'),
        sa.Column('triggered_by', postgresql.ENUM('auto', 'manual', name='retrain_trigger_type', create_type=False), nullable=False, comment='트리거 타입'),
        sa.Column('trigger_reason', sa.String(length=255), nullable=True, comment='트리거 사유'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='시작 일시'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='완료 일시'),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'completed', 'failed', name='retrain_status', create_type=False), nullable=False, server_default='pending', comment='상태'),
        sa.Column('new_model_version_id', postgresql.UUID(as_uuid=True), nullable=True, comment='신규 모델 버전 ID'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='성능 지표'),
        sa.Column('logs', sa.Text(), nullable=True, comment='로그'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='생성 일시'),
        sa.PrimaryKeyConstraint('job_id', name='pk_retraining_jobs')
    )
    op.create_index('idx_retraining_jobs_status', 'retraining_jobs', ['status'])
    op.create_index('idx_retraining_jobs_created_at', 'retraining_jobs', ['created_at'])

    # 12. ExternalServiceLog
    # Create service_name ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'service_name')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE service_name AS ENUM ('emailrep', 'numverify', 'bin_database', 'haveibeenpwned')")
    op.create_table(
        'external_service_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='로그 ID'),
        sa.Column('service_name', postgresql.ENUM('emailrep', 'numverify', 'bin_database', 'haveibeenpwned', name='service_name', create_type=False), nullable=False, comment='서비스 이름'),
        sa.Column('request_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='요청 데이터'),
        sa.Column('response_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='응답 데이터'),
        sa.Column('response_time_ms', sa.Integer(), nullable=False, comment='응답 시간'),
        sa.Column('status_code', sa.Integer(), nullable=True, comment='HTTP 상태 코드'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='에러 메시지'),
        sa.Column('called_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='호출 일시'),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=True, comment='거래 ID'),
        sa.PrimaryKeyConstraint('log_id', name='pk_external_service_logs')
    )
    op.create_index('idx_external_service_logs_service_name', 'external_service_logs', ['service_name'])
    op.create_index('idx_external_service_logs_called_at', 'external_service_logs', ['called_at'])
    op.create_index('idx_external_service_logs_transaction_id', 'external_service_logs', ['transaction_id'])

    # 13. BlacklistEntry
    # Create blacklist_entry_type ENUM if it doesn't exist
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'blacklist_entry_type')")).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE blacklist_entry_type AS ENUM ('device_id', 'ip_address', 'email', 'card_bin', 'shipping_address')")
    op.create_table(
        'blacklist_entries',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='항목 ID'),
        sa.Column('entry_type', postgresql.ENUM('device_id', 'ip_address', 'email', 'card_bin', 'shipping_address', name='blacklist_entry_type', create_type=False), nullable=False, comment='항목 타입'),
        sa.Column('entry_value', sa.String(length=255), nullable=False, comment='항목 값'),
        sa.Column('reason', sa.Text(), nullable=False, comment='차단 사유'),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=True, comment='추가한 사용자 ID'),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='추가 일시'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='만료 일시'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='활성화 여부'),
        sa.PrimaryKeyConstraint('entry_id', name='pk_blacklist_entries'),
        sa.UniqueConstraint('entry_type', 'entry_value', name='uq_blacklist_entry_type_value')
    )
    op.create_index('idx_blacklist_entries_entry_type', 'blacklist_entries', ['entry_type'])
    op.create_index('idx_blacklist_entries_is_active', 'blacklist_entries', ['is_active'])
    op.create_index('idx_blacklist_entries_expires_at', 'blacklist_entries', ['expires_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_blacklist_entries_expires_at', 'blacklist_entries')
    op.drop_index('idx_blacklist_entries_is_active', 'blacklist_entries')
    op.drop_index('idx_blacklist_entries_entry_type', 'blacklist_entries')
    op.drop_table('blacklist_entries')
    op.execute("DROP TYPE blacklist_entry_type")

    op.drop_index('idx_external_service_logs_transaction_id', 'external_service_logs')
    op.drop_index('idx_external_service_logs_called_at', 'external_service_logs')
    op.drop_index('idx_external_service_logs_service_name', 'external_service_logs')
    op.drop_table('external_service_logs')
    op.execute("DROP TYPE service_name")

    op.drop_index('idx_retraining_jobs_created_at', 'retraining_jobs')
    op.drop_index('idx_retraining_jobs_status', 'retraining_jobs')
    op.drop_table('retraining_jobs')
    op.execute("DROP TYPE retrain_status")
    op.execute("DROP TYPE retrain_trigger_type")

    op.drop_index('idx_data_drift_logs_alert_triggered', 'data_drift_logs')
    op.drop_index('idx_data_drift_logs_detected_at', 'data_drift_logs')
    op.drop_table('data_drift_logs')

    op.drop_index('idx_xai_explanations_generated_at', 'xai_explanations')
    op.drop_index('idx_xai_explanations_transaction_id', 'xai_explanations')
    op.drop_table('xai_explanations')

    op.drop_index('idx_feature_importances_rank', 'feature_importances')
    op.drop_index('idx_feature_importances_model_version_id', 'feature_importances')
    op.drop_table('feature_importances')

    op.drop_index('idx_ensemble_predictions_predicted_at', 'ensemble_predictions')
    op.drop_index('idx_ensemble_predictions_transaction_id', 'ensemble_predictions')
    op.drop_table('ensemble_predictions')
    op.execute("DROP TYPE prediction_decision")

    op.drop_index('idx_ml_model_versions_trained_at', 'ml_model_versions')
    op.drop_index('idx_ml_model_versions_is_active', 'ml_model_versions')
    op.drop_table('ml_model_versions')
    op.execute("DROP TYPE model_name")

    op.drop_index('idx_rule_executions_triggered_at', 'rule_executions')
    op.drop_index('idx_rule_executions_rule_id', 'rule_executions')
    op.drop_index('idx_rule_executions_transaction_id', 'rule_executions')
    op.drop_table('rule_executions')

    op.drop_index('idx_fraud_rules_priority', 'fraud_rules')
    op.drop_index('idx_fraud_rules_is_active', 'fraud_rules')
    op.drop_index('idx_fraud_rules_category', 'fraud_rules')
    op.drop_table('fraud_rules')
    op.execute("DROP TYPE rule_category")

    op.drop_index('idx_network_analysis_created_at', 'network_analysis')
    op.drop_index('idx_network_analysis_ip_address', 'network_analysis')
    op.drop_table('network_analysis')

    op.drop_index('idx_behavior_patterns_created_at', 'behavior_patterns')
    op.drop_index('idx_behavior_patterns_user_id', 'behavior_patterns')
    op.drop_table('behavior_patterns')

    op.drop_index('idx_device_fingerprints_blacklisted', 'device_fingerprints')
    op.drop_index('idx_device_fingerprints_created_at', 'device_fingerprints')
    op.drop_table('device_fingerprints')
