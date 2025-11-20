# PWA 아이콘 생성 가이드

## 필요한 아이콘 크기

PWA manifest.json에 정의된 아이콘들을 생성해야 합니다:

- `pwa-64x64.png` - 64x64px
- `pwa-192x192.png` - 192x192px (Android 홈 화면)
- `pwa-512x512.png` - 512x512px (Android 스플래시 스크린)
- `apple-touch-icon.png` - 180x180px (iOS 홈 화면)
- `favicon.ico` - 32x32px (브라우저 탭)

## 옵션 1: 온라인 도구 사용 (권장)

### PWA Asset Generator

1. https://www.pwabuilder.com/imageGenerator 방문
2. `pwa-icon-template.svg` 파일 업로드
3. "Generate" 클릭
4. 생성된 모든 아이콘을 `public/` 폴더에 저장

### RealFaviconGenerator

1. https://realfavicongenerator.net/ 방문
2. `pwa-icon-template.svg` 파일 업로드
3. 설정:
   - iOS: "Add a solid, single color background to fill the transparent regions"
   - Android: "Use a distinct picture for Android"
   - Windows: "Use a distinct picture for Windows"
4. 생성된 패키지 다운로드 및 압축 해제
5. 생성된 아이콘들을 `public/` 폴더에 복사

## 옵션 2: ImageMagick 사용

터미널에서 다음 명령어 실행:

```bash
# ImageMagick 설치 (필요한 경우)
# Windows: choco install imagemagick
# macOS: brew install imagemagick
# Linux: sudo apt-get install imagemagick

cd services/ecommerce/frontend/public

# SVG를 PNG로 변환 (다양한 크기)
magick pwa-icon-template.svg -resize 64x64 pwa-64x64.png
magick pwa-icon-template.svg -resize 192x192 pwa-192x192.png
magick pwa-icon-template.svg -resize 512x512 pwa-512x512.png
magick pwa-icon-template.svg -resize 180x180 apple-touch-icon.png
magick pwa-icon-template.svg -resize 32x32 favicon.ico

# 마스크 가능한 아이콘 (Safe Zone: 80%)
magick pwa-icon-template.svg -resize 192x192 -background transparent -gravity center -extent 240x240 pwa-192x192-maskable.png
magick pwa-icon-template.svg -resize 512x512 -background transparent -gravity center -extent 640x640 pwa-512x512-maskable.png
```

## 옵션 3: Figma/Adobe Illustrator 사용

1. `pwa-icon-template.svg`를 디자인 도구에서 열기
2. 브랜드 색상 및 로고에 맞게 수정
3. 각 크기로 내보내기:
   - PNG 형식
   - 배경 투명도 제거 (iOS의 경우)
   - Safe Zone 고려 (마스크 가능한 아이콘)

## 스플래시 스크린 이미지

### iOS 스플래시 스크린

iOS는 다양한 기기 크기에 맞는 스플래시 스크린이 필요합니다:

```bash
# 생성할 크기들
# iPhone SE: 640x1136
# iPhone 8: 750x1334
# iPhone 8 Plus: 1242x2208
# iPhone X: 1125x2436
# iPhone XR: 828x1792
# iPhone XS Max: 1242x2688
# iPad: 1536x2048
# iPad Pro 12.9": 2048x2732
```

### 스플래시 스크린 생성 명령어

```bash
# 예시: iPhone X 스플래시 스크린
magick -size 1125x2436 xc:"#3b82f6" \
  pwa-512x512.png -gravity center -composite \
  apple-launch-1125x2436.png
```

## 디자인 가이드라인

### 색상

- 주요 색상: `#3b82f6` (Blue 500)
- 보조 색상: `#1d4ed8` (Blue 700)
- 성공 색상: `#10b981` (Green 500)

### Safe Zone

마스크 가능한 아이콘 (maskable icon)은 다양한 모양으로 잘릴 수 있으므로:
- 중요한 콘텐츠는 중앙 80% 영역에 배치
- 외곽 20%는 배경 색상 또는 여백으로 유지

### 대비

- WCAG AA 기준 준수 (4.5:1 이상)
- 배경과 아이콘의 대비 확인

## 검증

생성된 아이콘을 다음 도구로 검증:

- https://maskable.app/ - 마스크 가능한 아이콘 테스트
- Lighthouse PWA 감사 - Chrome DevTools

## 최종 확인 사항

- [ ] pwa-64x64.png
- [ ] pwa-192x192.png
- [ ] pwa-512x512.png
- [ ] apple-touch-icon.png
- [ ] favicon.ico
- [ ] 마스크 가능한 아이콘 (선택사항)
- [ ] iOS 스플래시 스크린 (선택사항)
- [ ] manifest.json에서 아이콘 경로 확인
- [ ] 모든 아이콘이 로드되는지 브라우저에서 확인
