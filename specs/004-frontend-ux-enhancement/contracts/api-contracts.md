# API Contracts: Frontend UX Enhancement

**Feature**: 004-frontend-ux-enhancement
**Date**: 2025-11-19
**Base URL**: `http://localhost:8000` (development), `https://api.shopfds.com` (production)
**API Version**: v1

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:

```http
Authorization: Bearer <JWT_TOKEN>
```

JWT tokens are obtained through `/v1/auth/login` or OAuth endpoints. Tokens expire after 24 hours.

---

## 1. Search & Autocomplete API

### GET /v1/search/autocomplete

Returns search suggestions based on partial query.

**Query Parameters**:
- `q` (string, required): Search query (min 2 characters)
- `limit` (integer, optional): Max suggestions (default: 10, max: 20)

**Request Example**:
```http
GET /v1/search/autocomplete?q=iph&limit=5
```

**Response** (200 OK):
```json
{
  "suggestions": [
    {
      "type": "product",
      "text": "iPhone 15 Pro Max",
      "product_id": "550e8400-e29b-41d4-a716-446655440000",
      "image": "https://cdn.shopfds.com/products/iphone15.jpg",
      "price": 1490000
    },
    {
      "type": "brand",
      "text": "Apple iPhone",
      "category": "smartphones"
    },
    {
      "type": "category",
      "text": "iPhone Accessories"
    }
  ],
  "query": "iph"
}
```

---

### GET /v1/search

Full-text product search with filtering.

**Query Parameters**:
- `q` (string, required): Search query
- `category` (string, optional): Filter by category
- `min_price` (integer, optional): Minimum price
- `max_price` (integer, optional): Maximum price
- `brands` (string[], optional): Filter by brands (comma-separated)
- `in_stock` (boolean, optional): Only show in-stock products
- `sort` (string, optional): `relevance` | `price_asc` | `price_desc` | `newest` | `rating` (default: relevance)
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)

**Request Example**:
```http
GET /v1/search?q=laptop&min_price=500000&max_price=1500000&brands=samsung,lg&sort=price_asc&page=1&limit=20
```

**Response** (200 OK):
```json
{
  "products": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Samsung Galaxy Book3 Pro",
      "description": "14-inch AMOLED display, Intel Core i7...",
      "price": 1299000,
      "original_price": 1499000,
      "discount_percentage": 13,
      "image": "https://cdn.shopfds.com/products/galaxy-book3.jpg",
      "rating": 4.5,
      "review_count": 128,
      "stock": 15,
      "brand": "Samsung",
      "category": "laptops"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "limit": 20,
    "total_pages": 3
  },
  "filters": {
    "applied": {
      "min_price": 500000,
      "max_price": 1500000,
      "brands": ["samsung", "lg"]
    },
    "available": {
      "brands": ["Samsung", "LG", "Apple", "Dell"],
      "price_range": { "min": 450000, "max": 2500000 },
      "categories": ["laptops", "ultrabooks", "gaming-laptops"]
    }
  }
}
```

---

## 2. Product Reviews API

### GET /v1/products/{product_id}/reviews

Get reviews for a specific product.

**Path Parameters**:
- `product_id` (UUID, required): Product ID

**Query Parameters**:
- `rating` (integer, optional): Filter by star rating (1-5)
- `has_photos` (boolean, optional): Only reviews with photos
- `sort` (string, optional): `recent` | `rating_high` | `rating_low` | `helpful` (default: recent)
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 10, max: 50)

**Request Example**:
```http
GET /v1/products/550e8400-e29b-41d4-a716-446655440001/reviews?rating=5&has_photos=true&sort=helpful&page=1&limit=10
```

**Response** (200 OK):
```json
{
  "reviews": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440010",
      "user": {
        "id": "750e8400-e29b-41d4-a716-446655440020",
        "name": "John D.",
        "avatar": "https://cdn.shopfds.com/avatars/user123.jpg"
      },
      "rating": 5,
      "title": "Best laptop I've ever owned!",
      "content": "The display is stunning and the battery life is amazing. Highly recommend!",
      "images": [
        "https://cdn.shopfds.com/reviews/review1.jpg",
        "https://cdn.shopfds.com/reviews/review2.jpg"
      ],
      "helpful_count": 42,
      "is_verified_purchase": true,
      "created_at": "2025-11-15T09:30:00Z",
      "user_voted_helpful": false
    }
  ],
  "summary": {
    "average_rating": 4.5,
    "total_reviews": 128,
    "rating_distribution": {
      "5": 80,
      "4": 30,
      "3": 10,
      "2": 5,
      "1": 3
    }
  },
  "pagination": {
    "total": 80,
    "page": 1,
    "limit": 10,
    "total_pages": 8
  }
}
```

---

### POST /v1/reviews

Create a new product review (authenticated).

**Request Body**:
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440001",
  "rating": 5,
  "title": "Best laptop I've ever owned!",
  "content": "The display is stunning and the battery life is amazing. Highly recommend!",
  "images": [
    "https://cdn.shopfds.com/temp/upload123.jpg",
    "https://cdn.shopfds.com/temp/upload124.jpg"
  ]
}
```

**Validation**:
- `rating`: 1-5 (required)
- `content`: Min 10 characters, max 5000 (required)
- `title`: Max 200 characters (optional)
- `images`: Max 3 URLs (optional)
- User must have purchased and received the product

**Response** (201 Created):
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440010",
  "product_id": "550e8400-e29b-41d4-a716-446655440001",
  "rating": 5,
  "title": "Best laptop I've ever owned!",
  "content": "The display is stunning and the battery life is amazing. Highly recommend!",
  "images": [
    "https://cdn.shopfds.com/reviews/review1.jpg",
    "https://cdn.shopfds.com/reviews/review2.jpg"
  ],
  "helpful_count": 0,
  "is_verified_purchase": true,
  "created_at": "2025-11-19T10:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input (missing required fields, content too short)
- `403 Forbidden`: User hasn't purchased this product
- `409 Conflict`: User has already reviewed this product

---

### POST /v1/reviews/{review_id}/helpful

Mark a review as helpful (authenticated).

**Path Parameters**:
- `review_id` (UUID, required): Review ID

**Response** (200 OK):
```json
{
  "review_id": "650e8400-e29b-41d4-a716-446655440010",
  "helpful_count": 43,
  "user_voted": true
}
```

**Error Responses**:
- `409 Conflict`: User has already voted on this review

---

## 3. Wishlist API

### GET /v1/wishlist

Get current user's wishlist (authenticated).

**Query Parameters**:
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "750e8400-e29b-41d4-a716-446655440030",
      "product": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Samsung Galaxy Book3 Pro",
        "price": 1299000,
        "image": "https://cdn.shopfds.com/products/galaxy-book3.jpg",
        "rating": 4.5,
        "in_stock": true
      },
      "added_at": "2025-11-10T14:30:00Z"
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "limit": 20,
    "total_pages": 1
  }
}
```

---

### POST /v1/wishlist

Add product to wishlist (authenticated).

**Request Body**:
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response** (201 Created):
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440030",
  "product_id": "550e8400-e29b-41d4-a716-446655440001",
  "added_at": "2025-11-19T10:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Product does not exist
- `409 Conflict`: Product already in wishlist

---

### DELETE /v1/wishlist/{product_id}

Remove product from wishlist (authenticated).

**Path Parameters**:
- `product_id` (UUID, required): Product ID

**Response** (204 No Content)

---

## 4. OAuth API

### GET /v1/auth/oauth/{provider}

Initiate OAuth login flow.

**Path Parameters**:
- `provider` (string, required): `google` | `kakao` | `naver`

**Query Parameters**:
- `redirect_uri` (string, optional): Frontend callback URL (default: configured in backend)

**Response** (302 Redirect):
Redirects to OAuth provider's authorization URL.

**Example**:
```http
GET /v1/auth/oauth/google
→ Redirects to: https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=openid email profile
```

---

### GET /v1/auth/oauth/{provider}/callback

OAuth callback endpoint (handled by backend).

**Path Parameters**:
- `provider` (string, required): `google` | `kakao` | `naver`

**Query Parameters**:
- `code` (string, required): Authorization code from OAuth provider
- `state` (string, required): CSRF protection token

**Response** (302 Redirect):
Redirects to frontend with JWT token in query parameter:
```
https://shopfds.com/auth/callback?token=<JWT_TOKEN>&new_user=false
```

**JWT Payload**:
```json
{
  "sub": "750e8400-e29b-41d4-a716-446655440020",
  "email": "user@example.com",
  "name": "John Doe",
  "exp": 1700000000
}
```

---

## 5. Recommendation API

### GET /v1/recommendations/homepage

Get personalized product recommendations for homepage.

**Query Parameters**:
- `limit` (integer, optional): Max recommendations (default: 8, max: 20)

**Response** (200 OK):
```json
{
  "sections": [
    {
      "title": "Recommended for You",
      "products": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440001",
          "name": "Samsung Galaxy Book3 Pro",
          "price": 1299000,
          "image": "https://cdn.shopfds.com/products/galaxy-book3.jpg",
          "rating": 4.5
        }
      ],
      "reason": "Based on your browsing history"
    },
    {
      "title": "Popular This Week",
      "products": [...],
      "reason": "Trending in electronics"
    }
  ]
}
```

---

### GET /v1/products/{product_id}/related

Get related products for a specific product.

**Path Parameters**:
- `product_id` (UUID, required): Product ID

**Query Parameters**:
- `limit` (integer, optional): Max related products (default: 4, max: 12)

**Response** (200 OK):
```json
{
  "related_products": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "LG Gram 17",
      "price": 1899000,
      "image": "https://cdn.shopfds.com/products/lg-gram17.jpg",
      "rating": 4.7,
      "similarity_score": 0.85
    }
  ],
  "strategy": "same_category_popular"
}
```

---

## 6. Address Management API

### GET /v1/users/me/addresses

Get user's saved addresses (authenticated).

**Response** (200 OK):
```json
{
  "addresses": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440040",
      "name": "Home",
      "recipient": "John Doe",
      "phone": "010-1234-5678",
      "postal_code": "06234",
      "address_line1": "123 Gangnam-daero",
      "address_line2": "Apt 101",
      "city": "Seoul",
      "state": "Gangnam-gu",
      "country": "KR",
      "is_default": true,
      "created_at": "2025-11-01T10:00:00Z"
    },
    {
      "id": "850e8400-e29b-41d4-a716-446655440041",
      "name": "Office",
      "recipient": "John Doe",
      "phone": "010-1234-5678",
      "postal_code": "04524",
      "address_line1": "456 Teheran-ro",
      "address_line2": "Floor 10",
      "city": "Seoul",
      "state": "Gangnam-gu",
      "country": "KR",
      "is_default": false,
      "created_at": "2025-11-05T14:30:00Z"
    }
  ]
}
```

---

### POST /v1/users/me/addresses

Add a new address (authenticated).

**Request Body**:
```json
{
  "name": "Parents' House",
  "recipient": "Jane Doe",
  "phone": "010-9876-5432",
  "postal_code": "12345",
  "address_line1": "789 Main Street",
  "address_line2": "",
  "city": "Busan",
  "state": "Haeundae-gu",
  "country": "KR",
  "is_default": false
}
```

**Response** (201 Created):
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440042",
  "name": "Parents' House",
  "recipient": "Jane Doe",
  "phone": "010-9876-5432",
  "postal_code": "12345",
  "address_line1": "789 Main Street",
  "address_line2": "",
  "city": "Busan",
  "state": "Haeundae-gu",
  "country": "KR",
  "is_default": false,
  "created_at": "2025-11-19T10:00:00Z"
}
```

---

### PUT /v1/users/me/addresses/{address_id}

Update an existing address (authenticated).

**Path Parameters**:
- `address_id` (UUID, required): Address ID

**Request Body**: Same as POST

**Response** (200 OK): Updated address object

---

### DELETE /v1/users/me/addresses/{address_id}

Delete an address (authenticated).

**Path Parameters**:
- `address_id` (UUID, required): Address ID

**Response** (204 No Content)

**Error Responses**:
- `400 Bad Request`: Cannot delete default address (set another as default first)

---

## 7. Coupon API

### GET /v1/coupons/available

Get available coupons for current user (authenticated).

**Response** (200 OK):
```json
{
  "coupons": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440050",
      "code": "WELCOME5000",
      "description": "5000 KRW off on orders over 30000 KRW",
      "discount_type": "fixed_amount",
      "discount_value": 5000,
      "min_purchase_amount": 30000,
      "valid_until": "2025-12-31T23:59:59Z",
      "claimed": false
    },
    {
      "id": "950e8400-e29b-41d4-a716-446655440051",
      "code": "SAVE10",
      "description": "10% off, max 5000 KRW discount",
      "discount_type": "percentage",
      "discount_value": 10,
      "max_discount_amount": 5000,
      "min_purchase_amount": 0,
      "valid_until": "2025-11-30T23:59:59Z",
      "claimed": true,
      "used": false
    }
  ]
}
```

---

### POST /v1/coupons/validate

Validate a coupon code for current cart (authenticated).

**Request Body**:
```json
{
  "code": "SAVE10",
  "cart_total": 50000
}
```

**Response** (200 OK):
```json
{
  "valid": true,
  "coupon": {
    "id": "950e8400-e29b-41d4-a716-446655440051",
    "code": "SAVE10",
    "discount_type": "percentage",
    "discount_value": 10
  },
  "discount_amount": 5000,
  "final_total": 45000
}
```

**Error Responses**:
- `404 Not Found`: Coupon code does not exist
- `400 Bad Request`: Coupon expired, cart total below minimum, or already used

---

## 8. Product Comparison API

### GET /v1/products/compare

Compare multiple products side-by-side.

**Query Parameters**:
- `ids` (string[], required): Product IDs to compare (comma-separated, max 3)

**Request Example**:
```http
GET /v1/products/compare?ids=550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002,550e8400-e29b-41d4-a716-446655440003
```

**Response** (200 OK):
```json
{
  "products": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Samsung Galaxy Book3 Pro",
      "price": 1299000,
      "image": "https://cdn.shopfds.com/products/galaxy-book3.jpg",
      "rating": 4.5,
      "specs": {
        "processor": "Intel Core i7-1360P",
        "ram": "16GB",
        "storage": "512GB SSD",
        "display": "14-inch AMOLED",
        "battery": "63Wh",
        "weight": "1.17kg"
      }
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "LG Gram 17",
      "price": 1899000,
      "image": "https://cdn.shopfds.com/products/lg-gram17.jpg",
      "rating": 4.7,
      "specs": {
        "processor": "Intel Core i7-1260P",
        "ram": "16GB",
        "storage": "1TB SSD",
        "display": "17-inch IPS",
        "battery": "80Wh",
        "weight": "1.35kg"
      }
    }
  ],
  "common_specs": ["processor", "ram", "storage", "display", "battery", "weight"],
  "category": "laptops"
}
```

---

## 9. Push Notification API

### POST /v1/push/subscribe

Register a push notification subscription (authenticated).

**Request Body**:
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": {
    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls...",
    "auth": "tBHItJI5svbpez7KI4CCXg=="
  }
}
```

**Response** (201 Created):
```json
{
  "id": "a50e8400-e29b-41d4-a716-446655440060",
  "subscribed_at": "2025-11-19T10:00:00Z"
}
```

---

### DELETE /v1/push/unsubscribe

Unsubscribe from push notifications (authenticated).

**Response** (204 No Content)

---

## Error Responses

All API endpoints follow a consistent error format:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Rating must be between 1 and 5",
    "details": {
      "field": "rating",
      "value": 0
    }
  }
}
```

**Common Error Codes**:
- `400 Bad Request`: `INVALID_INPUT`, `VALIDATION_ERROR`
- `401 Unauthorized`: `MISSING_TOKEN`, `INVALID_TOKEN`, `TOKEN_EXPIRED`
- `403 Forbidden`: `INSUFFICIENT_PERMISSIONS`, `NOT_PURCHASED`
- `404 Not Found`: `RESOURCE_NOT_FOUND`
- `409 Conflict`: `ALREADY_EXISTS`, `DUPLICATE_VOTE`
- `429 Too Many Requests`: `RATE_LIMIT_EXCEEDED`
- `500 Internal Server Error`: `INTERNAL_ERROR`

---

## Rate Limiting

All API endpoints are rate-limited to prevent abuse:

- **Authenticated users**: 1000 requests per hour
- **Anonymous users**: 100 requests per hour
- **Search autocomplete**: 60 requests per minute

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1700000000
```

When rate limit is exceeded:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again in 1 hour."
  }
}
```

---

## Pagination

All list endpoints support cursor-based pagination:

**Request**:
```http
GET /v1/products?page=2&limit=20
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 2,
    "limit": 20,
    "total_pages": 8,
    "has_next": true,
    "has_prev": true
  }
}
```

---

## CORS

CORS is enabled for the following origins:
- `http://localhost:3000` (development)
- `https://shopfds.com` (production)
- `https://www.shopfds.com` (production)

Allowed methods: `GET, POST, PUT, DELETE, OPTIONS`
Allowed headers: `Content-Type, Authorization`

---

## Versioning

API version is included in the URL path: `/v1/...`

When breaking changes are introduced, a new version will be released (`/v2/...`) and the old version will be deprecated with a 6-month sunset period.

Deprecated endpoints will return a warning header:
```http
X-API-Deprecation: true
X-API-Sunset: 2026-06-01
```
