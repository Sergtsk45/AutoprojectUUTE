import React, { useState } from 'react';
import { X } from 'lucide-react';

interface EmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  purpose: 'sample' | 'partnership';
}

const EmailModal: React.FC<EmailModalProps> = ({ isOpen, onClose, purpose }) => {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [phone, setPhone] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  if (!isOpen) return null;
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsSubmitted(true);
      setIsSubmitting(false);
    }, 1000);
  };
  
  const title = purpose === 'sample' 
    ? 'Получить образец проекта' 
    : 'Получить специальные условия для партнёров';
  
  const buttonText = purpose === 'sample'
    ? 'Получить образец'
    : 'Отправить заявку';
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 relative">
        <button 
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>
        
        {!isSubmitted ? (
          <>
            <h3 className="text-xl font-bold mb-4 text-[#263238]">{title}</h3>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>
              
              {purpose === 'partnership' && (
                <>
                  <div className="mb-4">
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                      Имя *
                    </label>
                    <input
                      type="text"
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                      required
                    />
                  </div>
                  
                  <div className="mb-4">
                    <label htmlFor="company" className="block text-sm font-medium text-gray-700 mb-1">
                      Компания *
                    </label>
                    <input
                      type="text"
                      id="company"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                      required
                    />
                  </div>
                  
                  <div className="mb-4">
                    <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                      Телефон *
                    </label>
                    <input
                      type="tel"
                      id="phone"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                      required
                    />
                  </div>
                </>
              )}
              
              <div className="mt-6">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:bg-red-300"
                >
                  {isSubmitting ? 'Отправка...' : buttonText}
                </button>
              </div>
              
              <p className="mt-4 text-xs text-gray-500">
                Нажимая на кнопку, вы соглашаетесь с нашей политикой конфиденциальности
              </p>
            </form>
          </>
        ) : (
          <div className="text-center py-8">
            <div className="text-[#E53935] text-5xl mb-4">✓</div>
            <h3 className="text-xl font-bold mb-2 text-[#263238]">Спасибо!</h3>
            <p className="text-gray-600 mb-6">
              {purpose === 'sample' 
                ? 'Мы отправили образец проекта на ваш email.' 
                : 'Ваша заявка принята. Мы свяжемся с вами в ближайшее время.'}
            </p>
            <button
              onClick={onClose}
              className="bg-gray-200 hover:bg-gray-300 text-[#263238] font-medium py-2 px-4 rounded-md transition-colors"
            >
              Закрыть
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailModal;