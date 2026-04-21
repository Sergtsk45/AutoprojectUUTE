import React, { useState } from 'react';
import { X } from 'lucide-react';
import PrivacyPolicyModal from './PrivacyPolicyModal';
import { requestSample, createOrder, sendPartnershipRequest } from '../api';

interface EmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  purpose: 'sample' | 'partnership' | 'order';
  orderDefaults?: {
    circuits?: number;
    price?: number;
  };
  orderType?: 'express' | 'custom';
}

const EmailModal: React.FC<EmailModalProps> = ({ isOpen, onClose, purpose, orderDefaults, orderType }) => {
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [redirectUrl, setRedirectUrl] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      if (purpose === 'sample') {
        await requestSample(email);
      } else if (purpose === 'order') {
        const result = await createOrder({
          client_name: name,
          client_email: email,
          client_phone: phone || undefined,
          object_address: address || undefined,
          object_city: city,
          circuits: orderDefaults?.circuits,
          price: orderDefaults?.price,
          order_type: orderType ?? 'express',
        });
        setRedirectUrl(`/upload/${result.order_id}`);
      } else if (purpose === 'partnership') {
        await sendPartnershipRequest({
          name,
          company,
          email,
          phone,
        });
      }
      setIsSubmitted(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка. Попробуйте позже.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setName('');
    setCompany('');
    setPhone('');
    setAddress('');
    setCity('');
    setIsSubmitted(false);
    setError('');
    setRedirectUrl('');
    setIsPrivacyOpen(false);
    onClose();
  };

  const titles: Record<string, string> = {
    sample: 'Получить образец проекта',
    order: 'Заказать проект',
    partnership: 'Стать партнёром',
  };

  const buttonTexts: Record<string, string> = {
    sample: 'Получить образец',
    order: 'Создать заявку',
    partnership: 'Отправить заявку',
  };

  const showNameField = purpose === 'order' || purpose === 'partnership';
  const showPhoneField = purpose === 'order' || purpose === 'partnership';
  const showCompanyField = purpose === 'partnership';
  const showAddressField = purpose === 'order';
  const showCityField = purpose === 'order';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={handleClose}
          className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>

        {!isSubmitted ? (
          <>
            <h3 className="text-xl font-bold mb-4 text-[#263238]">{titles[purpose]}</h3>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {showNameField && (
                <div className="mb-4">
                  <label htmlFor="modal-name" className="block text-sm font-medium text-gray-700 mb-1">
                    Имя *
                  </label>
                  <input
                    type="text"
                    id="modal-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                    required
                  />
                </div>
              )}

              <div className="mb-4">
                <label htmlFor="modal-email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  id="modal-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              {showPhoneField && (
                <div className="mb-4">
                  <label htmlFor="modal-phone" className="block text-sm font-medium text-gray-700 mb-1">
                    Телефон {purpose === 'partnership' ? '*' : ''}
                  </label>
                  <input
                    type="tel"
                    id="modal-phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                    required={purpose === 'partnership'}
                  />
                </div>
              )}

              {showCompanyField && (
                <div className="mb-4">
                  <label htmlFor="modal-company" className="block text-sm font-medium text-gray-700 mb-1">
                    Компания *
                  </label>
                  <input
                    type="text"
                    id="modal-company"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                    required
                  />
                </div>
              )}

              {showAddressField && (
                <div className="mb-4">
                  <label htmlFor="modal-address" className="block text-sm font-medium text-gray-700 mb-1">
                    Почтовый адрес для отправки проекта
                  </label>
                  <input
                    type="text"
                    id="modal-address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="г. Москва, ул. Строителей, д. 5"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  />
                </div>
              )}

              {showCityField && (
                <div className="mb-4">
                  <label htmlFor="modal-city" className="block text-sm font-medium text-gray-700 mb-1">
                    Город объекта *
                  </label>
                  <input
                    type="text"
                    id="modal-city"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Москва"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                    required
                  />
                </div>
              )}

              <div className="mt-6">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:bg-red-300"
                >
                  {isSubmitting ? 'Отправка...' : buttonTexts[purpose]}
                </button>
              </div>

              <p className="mt-4 text-xs text-gray-500">
                Нажимая на кнопку, вы соглашаетесь с нашей{' '}
                <button
                  type="button"
                  onClick={() => setIsPrivacyOpen(true)}
                  className="underline hover:text-[#E53935] transition-colors"
                >
                  политикой конфиденциальности
                </button>
              </p>
            </form>
          </>
        ) : (
          <div className="text-center py-8">
            <div className="text-[#E53935] text-5xl mb-4">✓</div>
            <h3 className="text-xl font-bold mb-2 text-[#263238]">Спасибо!</h3>
            <p className="text-gray-600 mb-6">
              {purpose === 'sample' && 'Мы отправили образец проекта на ваш email.'}
              {purpose === 'order' && orderType === 'custom' && 'Заявка создана. Загрузите технические условия и заполните опросный лист для подбора оборудования.'}
              {purpose === 'order' && orderType !== 'custom' && 'Заявка создана. Сейчас вы будете перенаправлены на страницу загрузки технических условий.'}
              {purpose === 'partnership' && 'Ваша заявка принята. Мы свяжемся с вами в ближайшее время.'}
            </p>

            {purpose === 'order' && redirectUrl ? (
              <a
                href={redirectUrl}
                className="bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-6 rounded-md transition-colors inline-block"
              >
                Загрузить технические условия →
              </a>
            ) : (
              <button
                onClick={handleClose}
                className="bg-gray-200 hover:bg-gray-300 text-[#263238] font-medium py-2 px-4 rounded-md transition-colors"
              >
                Закрыть
              </button>
            )}
          </div>
        )}
      </div>
      <PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
    </div>
  );
};

export default EmailModal;
