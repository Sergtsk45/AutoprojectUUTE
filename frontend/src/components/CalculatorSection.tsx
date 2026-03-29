import React, { useState, useEffect } from 'react';
import EmailModal from './EmailModal';

const CalculatorSection: React.FC = () => {
  const [circuits, setCircuits] = useState(1);
  const [price, setPrice] = useState(0);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const prices: Record<number, number> = {
      1: 22500,
      2: 35000,
      3: 50000,
    };
    setPrice(prices[circuits] || 22500);
  }, [circuits]);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ru-RU').format(price);
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
            <div className="flex justify-between items-center mb-6">
              <span className="text-lg text-[#263238]">Стоимость проекта:</span>
              <span className="text-2xl font-bold text-[#E53935]">{formatPrice(price)} ₽</span>
            </div>

            <div className="bg-gray-50 p-4 rounded-md mb-6">
              <h4 className="font-medium text-[#263238] mb-2">В стоимость входит:</h4>
              <ul className="text-gray-600 space-y-1">
                <li>• Проектная документация в PDF формате</li>
                <li>• Согласование с теплоснабжающей организацией</li>
                <li>• Техническая поддержка на этапе монтажа</li>
              </ul>
            </div>

            <button
              onClick={() => setShowModal(true)}
              className="w-full bg-[#E53935] hover:bg-red-700 text-white font-medium py-3 px-6 rounded-md transition-colors"
            >
              Заказать проект за {formatPrice(price)} ₽
            </button>
          </div>
        </div>
      </div>

      <EmailModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        purpose="order"
        orderDefaults={{ circuits, price }}
      />
    </section>
  );
};

export default CalculatorSection;
