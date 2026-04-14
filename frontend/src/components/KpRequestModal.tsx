import React, { useState } from 'react';
import { X } from 'lucide-react';
import { sendKpRequest } from '../api';

interface KpRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const KpRequestModal: React.FC<KpRequestModalProps> = ({ isOpen, onClose }) => {
  const [organization, setOrganization] = useState('');
  const [responsibleName, setResponsibleName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [tuFile, setTuFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleClose = () => {
    setOrganization('');
    setResponsibleName('');
    setPhone('');
    setEmail('');
    setTuFile(null);
    setIsSubmitting(false);
    setIsSubmitted(false);
    setError('');
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tuFile) return;
    setIsSubmitting(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('organization', organization);
      formData.append('responsible_name', responsibleName);
      formData.append('phone', phone);
      formData.append('email', email);
      formData.append('tu_file', tuFile);
      await sendKpRequest(formData);
      setIsSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка. Попробуйте позже.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={handleClose}
          aria-label="Закрыть"
          className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>

        {!isSubmitted ? (
          <>
            <h3 className="text-xl font-bold mb-4 text-[#263238]">
              Запросить коммерческое предложение
            </h3>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="kp-organization" className="block text-sm font-medium text-gray-700 mb-1">
                  Наименование организации *
                </label>
                <input
                  type="text"
                  id="kp-organization"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-responsible-name" className="block text-sm font-medium text-gray-700 mb-1">
                  ФИО ответственного сотрудника *
                </label>
                <input
                  type="text"
                  id="kp-responsible-name"
                  value={responsibleName}
                  onChange={(e) => setResponsibleName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-phone" className="block text-sm font-medium text-gray-700 mb-1">
                  Телефон *
                </label>
                <input
                  type="tel"
                  id="kp-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-email" className="block text-sm font-medium text-gray-700 mb-1">
                  Эл. почта *
                </label>
                <input
                  type="email"
                  id="kp-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935]"
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="kp-tu-file" className="block text-sm font-medium text-gray-700 mb-1">
                  Техусловия на установку УУТЭ *
                </label>
                <input
                  type="file"
                  id="kp-tu-file"
                  accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                  onChange={(e) => setTuFile(e.target.files?.[0] ?? null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#E53935] text-sm"
                  required
                />
              </div>

              <div className="mt-6">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:bg-red-300"
                >
                  {isSubmitting ? 'Отправка...' : 'Запросить КП'}
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
              Ваш запрос принят. Мы свяжемся с вами в ближайшее время.
            </p>
            <button
              onClick={handleClose}
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

export default KpRequestModal;
