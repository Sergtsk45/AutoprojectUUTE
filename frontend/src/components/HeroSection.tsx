import React, { useState } from 'react';
import { Mail } from 'lucide-react';
import EmailModal from './EmailModal';
import heroBg from '../assets/hero-bg.jpg';

const HeroSection: React.FC = () => {
  const [showModal, setShowModal] = useState(false);

  return (
    <section 
      id="hero" 
      className="relative min-h-screen flex items-center pt-16 pb-16"
      style={{
        backgroundColor: '#263238'
      }}
    >
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: `url(${heroBg})`,
          opacity: 0.15
        }}
      ></div>
      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-3xl mx-auto text-center animate-fadeIn">
          <h1 className="text-white text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            Проект узла учёта тепловой энергии<br />
            за 3 дня –<br />
            готов к согласованию
          </h1>
          
          <h2 className="text-gray-200 text-xl md:text-2xl mb-8">
            Быстрее рынка в 10 раз. Онлайн-сервис по ПП 1034
          </h2>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            <button
              onClick={() => setShowModal(true)}
              className="bg-[#E53935] hover:bg-red-700 text-white font-medium py-3 px-6 rounded-md transition-colors flex items-center justify-center gap-2"
            >
              <Mail size={20} />
              Получить образец проекта
            </button>

            <a
              href="#questionnaire"
              className="bg-white hover:bg-gray-100 text-[#263238] font-medium py-3 px-6 rounded-md transition-colors flex items-center justify-center gap-2"
            >
              Заполнить опросный лист
            </a>
          </div>
          
          <div className="text-gray-300 text-sm">
            Документация готовится в соответствии с Постановлением Правительства №1034
          </div>
        </div>
      </div>

      {/* Email Modal */}
      <EmailModal isOpen={showModal} onClose={() => setShowModal(false)} purpose="sample" />
    </section>
  );
};

export default HeroSection;