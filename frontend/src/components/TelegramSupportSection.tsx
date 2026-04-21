import React from 'react';
import { MessageCircle } from 'lucide-react';

const TelegramSupportSection: React.FC = () => {
  // QR code would typically link to your telegram channel/bot
  const telegramQrUrl = "https://images.pexels.com/photos/8370377/pexels-photo-8370377.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2";
  const telegramLink = "https://t.me/your_support_bot";

  return (
    <section className="py-20 bg-white">
      <div className="container mx-auto px-4">
        <div className="max-w-4xl mx-auto bg-[#263238] rounded-lg shadow-lg overflow-hidden">
          <div className="flex flex-col md:flex-row">
            <div className="md:w-1/2 p-8 md:p-12">
              <h2 className="text-3xl font-bold text-white mb-4">
                Поддержка в Telegram
              </h2>

              <p className="text-gray-300 mb-6">
                Получите консультацию и ответы на вопросы в нашем Telegram-чате. Наши специалисты помогут заполнить опросный лист и будут сопровождать вас на каждом этапе от подготовки документов до согласования проекта.
              </p>

              <div className="space-y-4">
                <div className="flex items-center text-gray-300">
                  <div className="w-8 h-8 rounded-full bg-[#E53935] flex items-center justify-center mr-3">
                    <span className="text-white">1</span>
                  </div>
                  <span>Быстрые ответы в течение рабочего дня</span>
                </div>

                <div className="flex items-center text-gray-300">
                  <div className="w-8 h-8 rounded-full bg-[#E53935] flex items-center justify-center mr-3">
                    <span className="text-white">2</span>
                  </div>
                  <span>Профессиональные консультации</span>
                </div>

                <div className="flex items-center text-gray-300">
                  <div className="w-8 h-8 rounded-full bg-[#E53935] flex items-center justify-center mr-3">
                    <span className="text-white">3</span>
                  </div>
                  <span>Помощь с документами и согласованием</span>
                </div>
              </div>

              <a
                href={telegramLink}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-8 inline-flex items-center bg-[#E53935] hover:bg-red-700 text-white font-medium py-3 px-6 rounded-md transition-colors"
              >
                <MessageCircle size={20} className="mr-2" />
                Открыть чат
              </a>
            </div>

            <div className="md:w-1/2 bg-white p-8 md:p-12 flex items-center justify-center">
              <div className="text-center">
                <div className="mb-4 p-2 bg-white rounded-lg inline-block">
                  <img
                    src={telegramQrUrl}
                    alt="QR-код Telegram"
                    className="w-48 h-48 object-cover"
                  />
                </div>

                <p className="text-gray-600">
                  Отсканируйте QR-код для перехода в Telegram
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TelegramSupportSection;
