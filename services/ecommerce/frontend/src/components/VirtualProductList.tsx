/**
 * VirtualProductList Component
 * react-window를 사용한 가상 스크롤 (긴 상품 목록 성능 최적화)
 */

import { FixedSizeList as List } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";

interface Product {
  id: string;
  name: string;
  price: number;
  image_url?: string;
  stock_quantity: number;
  rating?: number;
  review_count?: number;
}

interface VirtualProductListProps {
  products: Product[];
  onProductClick: (productId: string) => void;
  itemHeight?: number; // 각 상품 카드 높이 (기본 200px)
}

export const VirtualProductList: React.FC<VirtualProductListProps> = ({
  products,
  onProductClick,
  itemHeight = 200,
}) => {
  // 각 상품 행 렌더링
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const product = products[index];

    return (
      <div style={style} className="px-4 py-2">
        <div
          className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer p-4"
          onClick={() => onProductClick(product.id)}
          onKeyPress={(e) => {
            if (e.key === "Enter") onProductClick(product.id);
          }}
          role="button"
          tabIndex={0}
          aria-label={`상품: ${product.name}, 가격: ${product.price.toLocaleString()}원`}
        >
          <div className="flex gap-4">
            {/* 상품 이미지 */}
            <div className="w-24 h-24 flex-shrink-0 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  No Image
                </div>
              )}
            </div>

            {/* 상품 정보 */}
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                {product.name}
              </h3>
              <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                {product.price.toLocaleString()}원
              </p>

              {/* 재고 정보 */}
              <p
                className={`text-sm mt-1 ${
                  product.stock_quantity > 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {product.stock_quantity > 0
                  ? `재고: ${product.stock_quantity}개`
                  : "품절"}
              </p>

              {/* 리뷰 정보 */}
              {product.rating && product.review_count ? (
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-yellow-500" aria-hidden="true">
                    ★
                  </span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {product.rating.toFixed(1)} ({product.review_count}개 리뷰)
                  </span>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full">
      <AutoSizer>
        {({ height, width }) => (
          <List
            height={height}
            itemCount={products.length}
            itemSize={itemHeight}
            width={width}
            overscanCount={5} // 스크롤 성능 최적화를 위한 버퍼
          >
            {Row}
          </List>
        )}
      </AutoSizer>
    </div>
  );
};

/**
 * VirtualGridProductList Component
 * 그리드 레이아웃 가상 스크롤 (3열 그리드)
 */
interface VirtualGridProductListProps {
  products: Product[];
  onProductClick: (productId: string) => void;
  columns?: number; // 열 개수 (기본 3)
  itemHeight?: number; // 각 행 높이 (기본 280px)
}

export const VirtualGridProductList: React.FC<VirtualGridProductListProps> = ({
  products,
  onProductClick,
  columns = 3,
  itemHeight = 280,
}) => {
  // 열 단위로 상품 그룹화
  const rows = [];
  for (let i = 0; i < products.length; i += columns) {
    rows.push(products.slice(i, i + columns));
  }

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const rowProducts = rows[index];

    return (
      <div style={style} className="px-4 py-2">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rowProducts.map((product) => (
            <div
              key={product.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer p-4"
              onClick={() => onProductClick(product.id)}
              onKeyPress={(e) => {
                if (e.key === "Enter") onProductClick(product.id);
              }}
              role="button"
              tabIndex={0}
              aria-label={`상품: ${product.name}, 가격: ${product.price.toLocaleString()}원`}
            >
              {/* 상품 이미지 */}
              <div className="w-full h-40 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden mb-3">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    No Image
                  </div>
                )}
              </div>

              {/* 상품 정보 */}
              <h3 className="text-base font-semibold text-gray-900 dark:text-white truncate">
                {product.name}
              </h3>
              <p className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                {product.price.toLocaleString()}원
              </p>

              {/* 재고 및 리뷰 */}
              <div className="flex justify-between items-center mt-2">
                <span
                  className={`text-xs ${
                    product.stock_quantity > 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {product.stock_quantity > 0 ? "재고 있음" : "품절"}
                </span>
                {product.rating && product.review_count ? (
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    ★ {product.rating.toFixed(1)} ({product.review_count})
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full">
      <AutoSizer>
        {({ height, width }) => (
          <List
            height={height}
            itemCount={rows.length}
            itemSize={itemHeight}
            width={width}
            overscanCount={3}
          >
            {Row}
          </List>
        )}
      </AutoSizer>
    </div>
  );
};
