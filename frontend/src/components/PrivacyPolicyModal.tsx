import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { PRIVACY_POLICY_HTML } from '../constants/privacyPolicyText';

interface PrivacyPolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PrivacyPolicyModal: React.FC<PrivacyPolicyModalProps> = ({ isOpen, onClose }) => {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;

    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current();
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg w-full max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h2 className="text-xl font-bold text-[#263238]">Политика конфиденциальности</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label="Закрыть"
          >
            <X size={24} />
          </button>
        </div>

        <div
          className="overflow-y-auto px-6 py-4
            [&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-[#263238] [&_h2]:mt-6 [&_h2]:mb-3
            [&_h3]:font-semibold [&_h3]:text-[#263238] [&_h3]:mt-5 [&_h3]:mb-2
            [&_p]:text-gray-700 [&_p]:mb-3 [&_p]:leading-relaxed
            [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-3
            [&_li]:text-gray-700 [&_li]:mb-1"
          dangerouslySetInnerHTML={{ __html: PRIVACY_POLICY_HTML }}
        />
      </div>
    </div>
  );
};

export default PrivacyPolicyModal;
