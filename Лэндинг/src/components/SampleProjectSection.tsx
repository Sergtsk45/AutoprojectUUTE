import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import sample1 from '../assets/sample1.jpg';
import sample2 from '../assets/sample2.jpg';
import sample3 from '../assets/sample3.jpg';
import sample4 from '../assets/sample4.jpg';

const SampleProjectSection: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  
  const projectImages = [
    sample1,
    sample2,
    sample3,
    sample4
  ];
  
  const nextSlide = () => {
    setCurrentSlide((prev) => (prev === projectImages.length - 1 ? 0 : prev + 1));
  };
  
  const prevSlide = () => {
    setCurrentSlide((prev) => (prev === 0 ? projectImages.length - 1 : prev - 1));
  };

  return (
    <section id="samples" className="py-20 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#263238] mb-16">
          Посмотрите пример проекта
        </h2>
        
        <div className="relative max-w-4xl mx-auto">
          {/* Carousel */}
          <div className="relative rounded-lg overflow-hidden shadow-lg aspect-[4/3]">
            {projectImages.map((image, index) => (
              <div
                key={index}
                className={`absolute inset-0 transition-opacity duration-500 ${
                  index === currentSlide ? 'opacity-100' : 'opacity-0 pointer-events-none'
                }`}
              >
                <img
                  src={image}
                  alt={`Пример проекта УУТЭ, страница ${index + 1}`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent pointer-events-none"></div>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-white text-4xl font-bold opacity-30 transform rotate-[-30deg] select-none">
                    ОБРАЗЕЦ
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {/* Navigation buttons */}
          <button
            onClick={prevSlide}
            className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 shadow-md transition-colors z-10"
          >
            <ChevronLeft size={24} className="text-[#263238]" />
          </button>
          
          <button
            onClick={nextSlide}
            className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 shadow-md transition-colors z-10"
          >
            <ChevronRight size={24} className="text-[#263238]" />
          </button>
          
          {/* Dots */}
          <div className="flex justify-center mt-6 space-x-2">
            {projectImages.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentSlide(index)}
                className={`w-3 h-3 rounded-full transition-colors ${
                  index === currentSlide ? 'bg-[#E53935]' : 'bg-gray-300 hover:bg-gray-400'
                }`}
              ></button>
            ))}
          </div>
        </div>
        
        <div className="text-center mt-10">
          <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
            Это пример реального проекта узла учета тепловой энергии. Мы предоставляем полный комплект документации в формате PDF.
          </p>
          
          <button 
            onClick={() => {
              const element = document.getElementById('hero');
              if (element) element.scrollIntoView({ behavior: 'smooth' });
            }}
            className="bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-6 rounded-md transition-colors"
          >
            Получить свой проект
          </button>
        </div>
      </div>
    </section>
  );
};

export default SampleProjectSection;