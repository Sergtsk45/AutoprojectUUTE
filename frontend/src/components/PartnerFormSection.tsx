import React, { useState } from 'react';
import EmailModal from './EmailModal';

const PartnerFormSection: React.FC = () => {
  const [showModal, setShowModal] = useState(false);

  return (
    <section id="contact" className="py-20 bg-gray-50">
      <div className="container mx-auto px-4">
        <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="flex flex-col md:flex-row">
            <div className="md:w-1/2 bg-[#263238] p-8 md:p-12 text-white">
              <h2 className="text-3xl font-bold mb-6">
                Специальные условия для партнёров
              </h2>
              
              <p className="mb-6 text-gray-300">
                Если вы проектная организация или монтажная компания, мы предлагаем выгодные условия сотрудничества:
              </p>
              
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <span className="text-[#E53935] mr-2">✓</span>
                  <span>Скидки до 30% от базовой стоимости</span>
                </li>
                <li className="flex items-start">
                  <span className="text-[#E53935] mr-2">✓</span>
                  <span>Приоритетная поддержка и консультации</span>
                </li>
                <li className="flex items-start">
                  <span className="text-[#E53935] mr-2">✓</span>
                  <span>Выделенный менеджер для ваших заказов</span>
                </li>
                <li className="flex items-start">
                  <span className="text-[#E53935] mr-2">✓</span>
                  <span>Возможность брендирования документации</span>
                </li>
              </ul>
              
              <button 
                onClick={() => setShowModal(true)}
                className="bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-6 rounded-md transition-colors"
              >
                Стать партнёром
              </button>
            </div>
            
            <div className="md:w-1/2 p-8 md:p-12">
              <h3 className="text-2xl font-bold text-[#263238] mb-6">
                Свяжитесь с нами
              </h3>
              
              <div className="space-y-6">
                <div>
                  <p className="text-gray-700 font-medium">Email:</p>
                  <a href="mailto:info@uute-project.ru" className="text-[#E53935] hover:underline">
                    info@uute-project.ru
                  </a>
                </div>
                
                <div>
                  <p className="text-gray-700 font-medium">Телефон:</p>
                  <a href="tel:+78001234567" className="text-[#E53935] hover:underline">
                    +7 (800) 123-45-67
                  </a>
                </div>
                
                <div>
                  <p className="text-gray-700 font-medium">Адрес:</p>
                  <address className="text-gray-600 not-italic">
                    123456, г. Москва, ул. Примерная, д. 10, офис 100
                  </address>
                </div>
                
                <div>
                  <p className="text-gray-700 font-medium">Время работы:</p>
                  <p className="text-gray-600">
                    Пн-Пт: 9:00 - 18:00<br />
                    Сб-Вс: выходные
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Partner Modal */}
      <EmailModal isOpen={showModal} onClose={() => setShowModal(false)} purpose="partnership" />
    </section>
  );
};

export default PartnerFormSection;