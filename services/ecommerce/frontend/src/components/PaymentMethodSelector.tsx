/**
 * 결제 수단 선택 컴포넌트
 *
 * 신용카드, Toss Payments, Kakao Pay 중 선택할 수 있습니다.
 */

import React, { useState } from 'react';

export type PaymentMethod = 'card' | 'toss' | 'kakao';

interface PaymentMethodSelectorProps {
  selectedMethod?: PaymentMethod;
  onSelect: (method: PaymentMethod) => void;
  cardInfo?: {
    cardNumber: string;
    cardExpiry: string;
    cardCvv: string;
  };
  onCardInfoChange?: (cardInfo: {
    cardNumber: string;
    cardExpiry: string;
    cardCvv: string;
  }) => void;
}

export default function PaymentMethodSelector({
  selectedMethod,
  onSelect,
  cardInfo,
  onCardInfoChange,
}: PaymentMethodSelectorProps) {
  const [localCardInfo, setLocalCardInfo] = useState({
    cardNumber: cardInfo?.cardNumber || '',
    cardExpiry: cardInfo?.cardExpiry || '',
    cardCvv: cardInfo?.cardCvv || '',
  });

  const handleCardInfoChange = (field: string, value: string) => {
    const updated = { ...localCardInfo, [field]: value };
    setLocalCardInfo(updated);
    onCardInfoChange?.(updated);
  };

  const formatCardNumber = (value: string) => {
    const cleaned = value.replace(/\D/g, '');
    const chunks = cleaned.match(/.{1,4}/g);
    return chunks ? chunks.join(' ') : cleaned;
  };

  const formatExpiry = (value: string) => {
    const cleaned = value.replace(/\D/g, '');
    if (cleaned.length >= 2) {
      return cleaned.slice(0, 2) + '/' + cleaned.slice(2, 4);
    }
    return cleaned;
  };

  return (
    <div className="space-y-4" data-testid="payment-method-selector">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        결제 수단
      </label>

      {/* 신용카드 */}
      <div
        className={`p-4 border rounded-lg cursor-pointer transition-all ${
          selectedMethod === 'card'
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-300'
        }`}
        onClick={() => onSelect('card')}
        data-testid="payment-method-card"
        data-selected={selectedMethod === 'card'}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white border border-gray-200 rounded flex items-center justify-center">
              💳
            </div>
            <div>
              <div className="font-medium">신용카드</div>
              <div className="text-sm text-gray-500">카드 정보 직접 입력</div>
            </div>
          </div>
          <div
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              selectedMethod === 'card'
                ? 'border-blue-500 bg-blue-500'
                : 'border-gray-300'
            }`}
          >
            {selectedMethod === 'card' && (
              <div className="w-2 h-2 bg-white rounded-full" />
            )}
          </div>
        </div>

        {/* 카드 정보 입력 필드 */}
        {selectedMethod === 'card' && (
          <div className="mt-4 space-y-3">
            <div>
              <label className="block text-sm text-gray-700 mb-1">카드 번호</label>
              <input
                type="text"
                value={formatCardNumber(localCardInfo.cardNumber)}
                onChange={(e) => {
                  const cleaned = e.target.value.replace(/\D/g, '');
                  if (cleaned.length <= 16) {
                    handleCardInfoChange('cardNumber', cleaned);
                  }
                }}
                placeholder="1234 5678 9012 3456"
                maxLength={19}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="card-number-input"
                onClick={(e) => e.stopPropagation()}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-700 mb-1">유효기간</label>
                <input
                  type="text"
                  value={formatExpiry(localCardInfo.cardExpiry)}
                  onChange={(e) => {
                    const cleaned = e.target.value.replace(/\D/g, '');
                    if (cleaned.length <= 4) {
                      handleCardInfoChange('cardExpiry', cleaned);
                    }
                  }}
                  placeholder="MM/YY"
                  maxLength={5}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="card-expiry-input"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">CVV</label>
                <input
                  type="text"
                  value={localCardInfo.cardCvv}
                  onChange={(e) => {
                    const cleaned = e.target.value.replace(/\D/g, '');
                    if (cleaned.length <= 3) {
                      handleCardInfoChange('cardCvv', cleaned);
                    }
                  }}
                  placeholder="123"
                  maxLength={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="card-cvv-input"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Toss Payments */}
      <div
        className={`p-4 border rounded-lg cursor-pointer transition-all ${
          selectedMethod === 'toss'
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-300'
        }`}
        onClick={() => onSelect('toss')}
        data-testid="payment-method-toss"
        data-selected={selectedMethod === 'toss'}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white border border-gray-200 rounded flex items-center justify-center">
              <span className="text-blue-600 font-bold text-lg">T</span>
            </div>
            <div>
              <div className="font-medium">토스페이</div>
              <div className="text-sm text-gray-500">간편 결제</div>
            </div>
          </div>
          <div
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              selectedMethod === 'toss'
                ? 'border-blue-500 bg-blue-500'
                : 'border-gray-300'
            }`}
          >
            {selectedMethod === 'toss' && (
              <div className="w-2 h-2 bg-white rounded-full" />
            )}
          </div>
        </div>
      </div>

      {/* Kakao Pay */}
      <div
        className={`p-4 border rounded-lg cursor-pointer transition-all ${
          selectedMethod === 'kakao'
            ? 'border-yellow-500 bg-yellow-50'
            : 'border-gray-300 hover:border-yellow-300'
        }`}
        onClick={() => onSelect('kakao')}
        data-testid="payment-method-kakao"
        data-selected={selectedMethod === 'kakao'}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-yellow-400 rounded flex items-center justify-center">
              <span className="text-brown-900 font-bold">K</span>
            </div>
            <div>
              <div className="font-medium">카카오페이</div>
              <div className="text-sm text-gray-500">간편 결제</div>
            </div>
          </div>
          <div
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              selectedMethod === 'kakao'
                ? 'border-yellow-500 bg-yellow-500'
                : 'border-gray-300'
            }`}
          >
            {selectedMethod === 'kakao' && (
              <div className="w-2 h-2 bg-white rounded-full" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
