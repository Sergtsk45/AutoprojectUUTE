import React, { useState, useEffect } from 'react';
import EmailModal from './EmailModal';

const CalculatorSection: React.FC = () => {
  const [circuits, setCircuits] = useState(1);
  const [price, setPrice] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [orderType, setOrderType] = useState<'express' | 'custom'>('express');

  useEffect(() => {
    const prices: Record<number, number> = {
      1: 22500,
      2: 35000,
      3: 50000,
    };
    setPrice(prices[circuits] || 22500);
  }, [circuits]);

  const formatPrice = (p: number) => new Intl.NumberFormat('ru-RU').format(p);

  /** Тариф «Экспресс» (1 контур) — фиксированная цена в калькуляторе и в заявке. */
  const EXPRESS_PRICE = 20000;
  const expressPrice = circuits === 1 ? EXPRESS_PRICE : price;

  const handleOrder = (type: 'express' | 'custom') => {
    setOrderType(type);
    setShowModal(true);
  };

  return (
    <section id="calculator" className="py-20 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#263238] mb-16">
          Рассчитайте стоимость проекта
        </h2>

        <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-sm p-8">
          <div className="mb-8">
            <label htmlFor="power-slider" className="block text-lg font-medium text-[#263238] mb-2">
              Количество контуров учёта:
            </label>

            <div className="flex items-center gap-4">
              <input
                type="range"
                id="power-slider"
                min="1"
                max="3"
                step="1"
                value={circuits}
                onChange={(e) => setCircuits(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#E53935]"
              />
              <span className="text-lg font-medium text-[#263238] w-20 text-right">
                {circuits} шт.
              </span>
            </div>

            <div className="flex justify-between mt-2 text-sm text-gray-500 relative">
              <span>1 контур</span>
              <span className="absolute left-1/2 -translate-x-1/2">2 контура</span>
              <span>3 контура</span>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-6 mt-6">
            <div className="bg-gray-50 p-4 rounded-md mb-6">
              <h4 className="font-medium text-[#263238] mb-2">В стоимость входит:</h4>
              <ul className="text-gray-600 space-y-1">
                <li>• Проектная документация в PDF формате</li>
                <li>• Согласование с теплоснабжающей организацией</li>
                <li>• Техническая поддержка на этапе монтажа</li>
              </ul>
            </div>

            <div className={`grid grid-cols-1 gap-4 ${circuits === 1 ? 'sm:grid-cols-2' : ''}`}>
              {/* Экспресс — только для 1 контура */}
              {circuits === 1 && (
                <div className="border-2 border-green-500 rounded-lg p-4 flex flex-col">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-base font-bold text-[#263238]">Экспресс</span>
                    <span className="text-xs bg-green-100 text-green-700 font-medium px-2 py-0.5 rounded-full">Популярный выбор</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">На базе электромагнитных расходомеров Эско 3Э · 3 рабочих дня</p>
                  <div className="mb-1">
                    <span className="text-xl font-bold text-green-600">{formatPrice(expressPrice)} ₽</span>
                  </div>
                  <p className="text-xs text-gray-400 line-through mb-4">{formatPrice(price)} ₽</p>
                  <button
                    onClick={() => handleOrder('express')}
                    className="mt-auto w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                  >
                    Выбрать
                  </button>
                </div>
              )}

              {/* Индивидуальный */}
              <div className="border-2 border-gray-200 rounded-lg p-4 flex flex-col">
                <div className="mb-1">
                  <span className="text-base font-bold text-[#263238]">Индивидуальный</span>
                </div>
                <p className="text-xs text-gray-500 mb-3">Выбор оборудования · опросный лист</p>
                <div className="mb-5">
                  <span className="text-xl font-bold text-[#263238]">{formatPrice(price)} ₽</span>
                </div>
                <button
                  onClick={() => handleOrder('custom')}
                  className="mt-auto w-full bg-[#263238] hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  Выбрать
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <EmailModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        purpose="order"
        orderDefaults={{ circuits, price: orderType === 'express' ? expressPrice : price }}
        orderType={orderType}
      />
    </section>
  );
};

export default CalculatorSection;
