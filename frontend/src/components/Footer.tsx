import React, { useState } from 'react';
import { SITE_CONTACT, SITE_REQUISITES } from '../constants/siteLegal';
import PrivacyPolicyModal from './PrivacyPolicyModal';

const Footer: React.FC = () => {
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
  return (
    <footer className="bg-[#263238] text-white py-12">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold mb-4">УУТЭ Проект</h3>
            <p className="text-gray-300 mb-4">
              Онлайн-сервис по разработке проектов узлов учета тепловой энергии в соответствии с ПП 1034.
            </p>
            <p className="text-gray-300">
              © 2025 УУТЭ Проект. Все права защищены.
            </p>
          </div>
          
          <div>
            <h3 className="text-xl font-bold mb-4">Контакты</h3>
            <ul className="space-y-2 text-gray-300">
              <li>
                <strong className="font-medium">Адрес:</strong> {SITE_CONTACT.address}
              </li>
              <li>
                <strong className="font-medium">Телефон:</strong>{' '}
                <a href={`tel:${SITE_CONTACT.phoneTel}`} className="hover:text-[#E53935] transition-colors">
                  {SITE_CONTACT.phoneDisplay}
                </a>
              </li>
              <li>
                <strong className="font-medium">Email:</strong>{' '}
                <a href={`mailto:${SITE_CONTACT.email}`} className="hover:text-[#E53935] transition-colors">
                  {SITE_CONTACT.email}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xl font-bold mb-4">Реквизиты</h3>
            <ul className="space-y-2 text-gray-300">
              <li><strong className="font-medium">{SITE_REQUISITES.legalName}</strong></li>
              <li>{SITE_REQUISITES.innKpp}</li>
              <li>{SITE_REQUISITES.ogrn}</li>
              <li>{SITE_REQUISITES.rs}</li>
              <li>{SITE_REQUISITES.ks}</li>
              <li>{SITE_REQUISITES.bik}</li>
              <li>{SITE_REQUISITES.bank}</li>
            </ul>
          </div>
        </div>
        
        <div className="pt-6 border-t border-gray-700">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); setIsPrivacyOpen(true); }}
                className="text-gray-300 hover:text-[#E53935] transition-colors mr-6 cursor-pointer"
              >
                Политика конфиденциальности
              </a>
              <a href="#" className="text-gray-300 hover:text-[#E53935] transition-colors">
                Договор оферты
              </a>
            </div>
            
            <div className="flex items-center space-x-4">
              <a 
                href="#" 
                className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center hover:bg-[#E53935] transition-colors"
              >
                <span className="sr-only">Telegram</span>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M20.572 4.551a1.75 1.75 0 0 0-1.75-1.11c-.789.099-1.695.391-2.745.812a27.643 27.643 0 0 0-6.34 3.657 28.387 28.387 0 0 0-5.23 5.224 27.644 27.644 0 0 0-3.656 6.34c-.42 1.05-.713 1.956-.812 2.744a1.75 1.75 0 0 0 1.11 1.75c.29.111.61.109.898-.005l5.894-2.391a1.75 1.75 0 0 0 .817-.64l2.368-3.312a.25.25 0 0 1 .386-.034l4.48 4.09a1.75 1.75 0 0 0 2.66-.531l5.134-10.994a1.75 1.75 0 0 0-.214-1.6zm-1.949 1.107l-5.134 10.995a.25.25 0 0 1-.38.076l-4.48-4.09a1.75 1.75 0 0 0-2.701.239l-2.368 3.312a.25.25 0 0 1-.116.091l-5.855 2.375a.25.25 0 0 1-.01-.219c.062-.517.32-1.313.683-2.235a26.145 26.145 0 0 1 3.46-5.997 26.889 26.889 0 0 1 4.95-4.944 26.145 26.145 0 0 1 5.996-3.46c.922-.364 1.718-.622 2.236-.683a.25.25 0 0 1 .277.202c.014.048.015.083.005.113a.236.236 0 0 1-.063.105z"/>
                </svg>
              </a>
              <a 
                href="#" 
                className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center hover:bg-[#E53935] transition-colors"
              >
                <span className="sr-only">WhatsApp</span>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M12.001 2a9.96 9.96 0 0 0-7.064 2.921A9.96 9.96 0 0 0 2.001 12c0 1.86.52 3.69 1.503 5.29L2 22l4.842-1.302A9.977 9.977 0 0 0 12 22a9.96 9.96 0 0 0 7.064-2.922A9.96 9.96 0 0 0 22 12c0-2.751-1.072-5.342-3.02-7.296A10.138 10.138 0 0 0 12 2Zm0 1.5c2.28 0 4.43.887 6.033 2.506A8.5 8.5 0 0 1 20.5 12c0 2.29-.881 4.446-2.502 6.064A8.476 8.476 0 0 1 12 20.5a8.545 8.545 0 0 1-4.09-1.037l-.349-.187-.393.103-2.165.581.585-2.122.12-.435-.2-.394A8.456 8.456 0 0 1 3.5 12c0-2.28.887-4.43 2.506-6.033A8.476 8.476 0 0 1 12 3.5ZM8.85 7.267c-.12-.285-.326-.264-.489-.26-.087.003-.188.007-.289.007a.558.558 0 0 0-.404.189c-.141.154-.54.525-.54 1.28s.551 1.49.628 1.595c.078.103 1.143 1.72 2.754 2.398.447.195.786.29 1.053.377.442.139.845.124 1.164.079.354-.052 1.088-.44 1.241-.87.153-.428.153-.796.107-.873-.045-.078-.173-.127-.365-.222-.188-.095-1.117-.55-1.292-.61-.173-.062-.3-.093-.426.094-.13.186-.494.61-.605.735-.112.124-.224.139-.412.044-.187-.095-.794-.293-1.51-.932-.56-.497-.938-1.11-1.047-1.298-.111-.186-.013-.287.084-.38.087-.084.194-.219.29-.328.098-.11.13-.187.195-.312.065-.124.033-.232-.016-.326-.05-.094-.444-1.055-.608-1.445Z"/>
                </svg>
              </a>
              <a 
                href="#" 
                className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center hover:bg-[#E53935] transition-colors"
              >
                <span className="sr-only">Email</span>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M3 5.75C3 4.784 3.784 4 4.75 4h14.5c.966 0 1.75.784 1.75 1.75v12.5A1.75 1.75 0 0 1 19.25 20H4.75A1.75 1.75 0 0 1 3 18.25V5.75Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h14.5a.25.25 0 0 0 .25-.25V5.75a.25.25 0 0 0-.25-.25H4.75Z"/>
                  <path d="M4 13.28V5.75c0-.138.112-.25.25-.25h15.5c.138 0 .25.112.25.25v7.53c0 .403.39.615.698.327l4.564-4.276a.75.75 0 0 1 1.023 1.095l-4.563 4.274a2.25 2.25 0 0 1-3.223-.324L14.724 10 9.03 15.263a2.25 2.25 0 0 1-3.097.289l-5.5-4.5a.75.75 0 0 1 .954-1.152l5.5 4.5c.307.252.735.252 1.042 0l5.694-5.263L9.05 4.259c-.307-.253-.735-.253-1.042 0L2.953 8.89a.75.75 0 0 1-.954-1.152l5.055-4.63a2.25 2.25 0 0 1 3.097 0l4.57 4.254a.25.25 0 0 0 .348 0l4.571-4.254a2.25 2.25 0 0 1 3.097 0l4.554 4.28a.75.75 0 0 1-1.026 1.095l-4.554-4.28a.25.25 0 0 0-.344 0L17.821 8.46a.75.75 0 0 1-1.042 0l-4.55-4.242a.25.25 0 0 0-.348 0L7.33 8.46a.75.75 0 0 1-1.042 0L2.977 5.233a.75.75 0 0 1 1.026-1.095l3.26 3.226a.25.25 0 0 0 .348 0l4.55-4.241a2.25 2.25 0 0 1 3.097 0l4.55 4.242a.25.25 0 0 0 .348 0l3.309-3.226a.75.75 0 0 1 1.026 1.095L20.28 9.264a.25.25 0 0 0 .37-.334V5.75a.25.25 0 0 0-.25-.25H4.75a.25.25 0 0 0-.25.25v7.53a.75.75 0 0 1-1.5 0Z"/>
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
      <PrivacyPolicyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
    </footer>
  );
};

export default Footer;