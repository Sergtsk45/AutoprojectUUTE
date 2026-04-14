import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
}

const FAQSection: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  
  const faqItems: FAQItem[] = [
    {
      question: 'Какие сроки выполнения проекта УУТЭ?',
      answer: 'Стандартный срок выполнения проекта узла учета тепловой энергии - 3 рабочих дня с момента оплаты и предоставления всех необходимых исходных данных.'
    },
    {
      question: 'Сколько стоит проект УУТЭ?',
      answer: 'Стоимость проекта зависит от мощности теплопотребления объекта. Базовая стоимость начинается от 30 000 рублей, со скидкой — от 20 000 рублей. Для расчета точной стоимости воспользуйтесь нашим калькулятором на сайте или свяжитесь с нашими специалистами.'
    },
    {
      question: 'Что делать, если РСО требует доработать проект?',
      answer: 'Мы гарантируем согласование проекта с ресурсоснабжающей организацией. В случае если РСО выдаст замечания к проекту, мы внесем все необходимые корректировки бесплатно и в кратчайшие сроки.'
    },
    {
      question: 'Делаете ли вы проекты в BIM?',
      answer: 'Да, мы выполняем проектирование узлов учета тепловой энергии в BIM-моделях по стандарту IFC. Стоимость проектирования в BIM обсуждается индивидуально и зависит от сложности объекта.'
    },
    {
      question: 'Какие есть способы оплаты?',
      answer: 'Мы принимаем оплату различными способами: безналичный расчет для юридических лиц, оплата банковской картой через сайт, электронные платежи (ЮKassa). При необходимости можем предоставить рассрочку платежа.'
    },
    {
      question: 'Предоставляете ли вы услуги авторского надзора?',
      answer: 'Да, мы предоставляем услуги авторского надзора при монтаже узла учета тепловой энергии. Это гарантирует, что узел будет смонтирован в полном соответствии с проектной документацией и требованиями нормативных документов.'
    }
  ];
  
  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section id="faq" className="py-20 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#263238] mb-16">
          Часто задаваемые вопросы
        </h2>
        
        <div className="max-w-3xl mx-auto">
          <div className="space-y-4">
            {faqItems.map((item, index) => (
              <div 
                key={index} 
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                <button
                  className="w-full px-6 py-4 text-left flex justify-between items-center focus:outline-none"
                  onClick={() => toggleItem(index)}
                >
                  <span className="font-medium text-[#263238]">{item.question}</span>
                  {openIndex === index ? (
                    <ChevronUp size={20} className="text-[#E53935]" />
                  ) : (
                    <ChevronDown size={20} className="text-[#E53935]" />
                  )}
                </button>
                
                <div 
                  className={`px-6 pb-4 text-gray-600 ${
                    openIndex === index ? 'block' : 'hidden'
                  }`}
                >
                  <p>{item.answer}</p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-12 text-center">
            <p className="text-gray-600 mb-6">
              Не нашли ответ на свой вопрос? Свяжитесь с нами, и мы с радостью поможем!
            </p>
            
            <a 
              href="#contact" 
              className="bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-6 rounded-md transition-colors"
            >
              Задать вопрос
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FAQSection;