-- 샘플 상품 데이터 삽입
INSERT INTO products (id, name, description, price, stock_quantity, category, image_url, status, created_at, updated_at) VALUES
-- 전자기기
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '갤럭시 S24 Ultra', '최신 삼성 플래그십 스마트폰. 200MP 카메라, S펜 내장, 6.8인치 AMOLED 디스플레이', 1450000, 50, '전자기기', 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500', 'available', NOW(), NOW()),
('b1ffcd99-9c0b-4ef8-bb6d-6bb9bd380a22', '아이폰 15 Pro', 'Apple의 최신 프로 모델. A17 Pro 칩, 티타늄 디자인, 48MP 메인 카메라', 1550000, 35, '전자기기', 'https://images.unsplash.com/photo-1592286927505-f0e2c0b1e5d1?w=500', 'available', NOW(), NOW()),
('c2ffcd99-9c0b-4ef8-bb6d-6bb9bd380a33', '맥북 프로 14인치', 'M3 Pro 칩 탑재. 14인치 Liquid Retina XDR 디스플레이, 18시간 배터리', 2890000, 20, '전자기기', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500', 'available', NOW(), NOW()),
('d3ffcd99-9c0b-4ef8-bb6d-6bb9bd380a44', '에어팟 프로 2세대', '능동 소음 차단, 적응형 투명 모드, MagSafe 충전 케이스', 359000, 100, '전자기기', 'https://images.unsplash.com/photo-1606841837239-c5a1a4a07af7?w=500', 'available', NOW(), NOW()),
-- 의류
('e4ffcd99-9c0b-4ef8-bb6d-6bb9bd380a55', '나이키 에어맥스 270', '편안한 쿠셔닝과 세련된 디자인. 다양한 컬러 옵션 제공', 189000, 80, '의류', 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500', 'available', NOW(), NOW()),
('f5ffcd99-9c0b-4ef8-bb6d-6bb9bd380a66', '아디다스 울트라부스트', 'BOOST 미드솔로 최고의 쿠셔닝 제공. 러닝에 최적화', 220000, 60, '의류', 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500', 'available', NOW(), NOW()),
('06ffcd99-9c0b-4ef8-bb6d-6bb9bd380a77', '노스페이스 다운 재킷', '700 필 파워 구스 다운. 방수 및 방풍 기능', 329000, 45, '의류', 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500', 'available', NOW(), NOW()),
-- 도서
('17ffcd99-9c0b-4ef8-bb6d-6bb9bd380a88', '클린 코드 (Clean Code)', '로버트 C. 마틴 저. 애자일 소프트웨어 장인 정신', 33000, 150, '도서', 'https://images.unsplash.com/photo-1532012197267-da84d127e765?w=500', 'available', NOW(), NOW()),
('28ffcd99-9c0b-4ef8-bb6d-6bb9bd380a99', '디자인 패턴', 'GoF의 디자인 패턴. 소프트웨어 설계의 고전', 38000, 120, '도서', 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500', 'available', NOW(), NOW()),
('39ffcd99-9c0b-4ef8-bb6d-6bb9bd380aaa', '파이썬 코딩의 기술', '브렛 슬래킨 저. Effective Python 2nd Edition', 30000, 100, '도서', 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=500', 'available', NOW(), NOW()),
-- 가구
('4affcd99-9c0b-4ef8-bb6d-6bb9bd380abb', '에르고휴먼 의자', '메쉬 소재 인체공학 의자. 요추 지지대, 팔걸이 조절 가능', 890000, 25, '가구', 'https://images.unsplash.com/photo-1580480055273-228ff5388ef8?w=500', 'available', NOW(), NOW()),
('5bffcd99-9c0b-4ef8-bb6d-6bb9bd380acc', '높이조절 책상', '전동 높이 조절 스탠딩 데스크. 140x70cm, 메모리 기능', 550000, 30, '가구', 'https://images.unsplash.com/photo-1595515106969-1ce29566ff1c?w=500', 'available', NOW(), NOW()),
-- 식품
('6cffcd99-9c0b-4ef8-bb6d-6bb9bd380add', '프리미엄 아라비카 원두', '에티오피아 예가체프 원두 1kg. 플로럴한 향과 부드러운 산미', 35000, 200, '식품', 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500', 'available', NOW(), NOW()),
('7dffcd99-9c0b-4ef8-bb6d-6bb9bd380aee', '유기농 녹차 세트', '제주 유기농 녹차 100g x 3종 세트. 우전, 세작, 중작', 42000, 150, '식품', 'https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?w=500', 'available', NOW(), NOW()),
-- 재고 부족/품절 상품 (테스트용)
('8effcd99-9c0b-4ef8-bb6d-6bb9bd380aff', '한정판 스니커즈', '한정 수량 스페셜 에디션. 재입고 미정', 450000, 3, '의류', 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=500', 'available', NOW(), NOW()),
('9fffcd99-9c0b-4ef8-bb6d-6bb9bd380b00', '품절된 상품', '현재 재고가 없습니다. 곧 재입고 예정', 99000, 0, '전자기기', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500', 'out_of_stock', NOW(), NOW());
