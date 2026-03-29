import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';

const Header: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? 'bg-white shadow-md py-2' : 'bg-transparent py-4'
      }`}
    >
      <div className="container mx-auto px-4 flex justify-between items-center">
        <div className="flex items-center">
          <span className={`text-2xl font-bold ${isScrolled ? 'text-[#263238]' : 'text-white'}`}>
            УУТЭ
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          <a href="#why-us" className={`font-medium transition-colors ${isScrolled ? 'text-[#263238] hover:text-[#E53935]' : 'text-white hover:text-gray-200'}`}>
            Преимущества
          </a>
          <a href="#process" className={`font-medium transition-colors ${isScrolled ? 'text-[#263238] hover:text-[#E53935]' : 'text-white hover:text-gray-200'}`}>
            Процесс
          </a>
          <a href="#samples" className={`font-medium transition-colors ${isScrolled ? 'text-[#263238] hover:text-[#E53935]' : 'text-white hover:text-gray-200'}`}>
            Примеры
          </a>
          <a href="#calculator" className={`font-medium transition-colors ${isScrolled ? 'text-[#263238] hover:text-[#E53935]' : 'text-white hover:text-gray-200'}`}>
            Калькулятор
          </a>
          <a href="#faq" className={`font-medium transition-colors ${isScrolled ? 'text-[#263238] hover:text-[#E53935]' : 'text-white hover:text-gray-200'}`}>
            FAQ
          </a>
          <a 
            href="#contact" 
            className="bg-[#E53935] text-white font-medium py-2 px-4 rounded-md hover:bg-red-700 transition-colors"
          >
            Связаться
          </a>
        </nav>

        {/* Mobile Menu Button */}
        <button 
          className="md:hidden p-2"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          {isMenuOpen ? (
            <X className={isScrolled ? 'text-[#263238]' : 'text-white'} size={24} />
          ) : (
            <Menu className={isScrolled ? 'text-[#263238]' : 'text-white'} size={24} />
          )}
        </button>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-white py-4 px-4 shadow-lg">
          <nav className="flex flex-col space-y-4">
            <a 
              href="#why-us" 
              className="text-[#263238] font-medium py-2 hover:text-[#E53935]"
              onClick={() => setIsMenuOpen(false)}
            >
              Преимущества
            </a>
            <a 
              href="#process" 
              className="text-[#263238] font-medium py-2 hover:text-[#E53935]"
              onClick={() => setIsMenuOpen(false)}
            >
              Процесс
            </a>
            <a 
              href="#samples" 
              className="text-[#263238] font-medium py-2 hover:text-[#E53935]"
              onClick={() => setIsMenuOpen(false)}
            >
              Примеры
            </a>
            <a 
              href="#calculator" 
              className="text-[#263238] font-medium py-2 hover:text-[#E53935]"
              onClick={() => setIsMenuOpen(false)}
            >
              Калькулятор
            </a>
            <a 
              href="#faq" 
              className="text-[#263238] font-medium py-2 hover:text-[#E53935]"
              onClick={() => setIsMenuOpen(false)}
            >
              FAQ
            </a>
            <a 
              href="#contact" 
              className="bg-[#E53935] text-white font-medium py-2 px-4 rounded-md text-center hover:bg-red-700"
              onClick={() => setIsMenuOpen(false)}
            >
              Связаться
            </a>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;