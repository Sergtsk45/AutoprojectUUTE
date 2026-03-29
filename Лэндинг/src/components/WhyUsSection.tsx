import React from 'react';
import { Clock, Check, RussianRuble as Ruble, CreditCard } from 'lucide-react';

const WhyUsSection: React.FC = () => {
  const benefits = [
    {
      icon: <Clock size={48} className="text-[#E53935]" />,
      title: '3 дня',
      description: 'От заявки до готового проекта УУТЭ'
    },
    {
      icon: <Check size={48} className="text-[#E53935]" />,
      title: '100% согласование',
      description: 'Гарантируем согласование в РСО'
    },
    {
      icon: <Ruble size={48} className="text-[#E53935]" />,
      title: 'Фиксированная цена',
      description: 'Без скрытых доплат и комиссий'
    },
    {
      icon: <CreditCard size={48} className="text-[#E53935]" />,
      title: 'Онлайн-оплата',
      description: 'Удобные способы оплаты'
    }
  ];

  return (
    <section id="why-us" className="py-20 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#263238] mb-16">
          Почему выбирают нас
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {benefits.map((benefit, index) => (
            <div 
              key={index} 
              className="bg-white rounded-lg p-6 text-center shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex justify-center mb-4">
                {benefit.icon}
              </div>
              <h3 className="text-xl font-bold text-[#263238] mb-2">
                {benefit.title}
              </h3>
              <p className="text-gray-600">
                {benefit.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default WhyUsSection;