import React, { useState } from 'react';
import { FileText, Clock3, FileCheck } from 'lucide-react';
import KpRequestModal from './KpRequestModal';

/** Источник: `docs/opros_list_form.pdf`; копия в `frontend/public/downloads/` для прод-сборки. */
const SURVEY_FORM_PDF_HREF = '/downloads/opros_list_form.pdf';
const SURVEY_FORM_PDF_DOWNLOAD_AS = 'opros_list_form.pdf';

type StepAction = {
  text: string;
  link: string;
  download?: string;
};

const ProcessSection: React.FC = () => {
  const [kpModalOpen, setKpModalOpen] = useState(false);

  const steps: Array<{
    icon: React.ReactNode;
    title: string;
    description: string;
    action: StepAction;
  }> = [
    {
      icon: <FileText size={48} className="text-[#E53935]" />,
      title: 'Шаг 1',
      description: 'Скачайте опросный лист и загрузите ТУ',
      action: {
        text: 'Скачать опросный лист',
        link: SURVEY_FORM_PDF_HREF,
        download: SURVEY_FORM_PDF_DOWNLOAD_AS,
      }
    },
    {
      icon: <Clock3 size={48} className="text-[#E53935]" />,
      title: 'Шаг 2',
      description: 'Получите коммерческое предложение за 15 минут',
      action: {
        text: 'Запросить КП',
        link: '#'
      }
    },
    {
      icon: <FileCheck size={48} className="text-[#E53935]" />,
      title: 'Шаг 3',
      description: 'Через 3 дня получите готовый проект в PDF формате',
      action: {
        text: 'Заказать проект',
        link: '#calculator'
      }
    }
  ];

  return (
    <section id="process" className="py-20 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#263238] mb-16">
          Процесс работы в 3 шага
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => (
            <div 
              key={index} 
              className="bg-white rounded-lg p-8 text-center shadow-sm hover:shadow-md transition-shadow relative"
            >
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-1/2 right-0 transform translate-x-1/2 -translate-y-1/2 z-10">
                  <div className="w-8 h-8 rounded-full bg-[#E53935] text-white flex items-center justify-center">
                    →
                  </div>
                </div>
              )}
              
              <div className="flex justify-center mb-6">
                {step.icon}
              </div>
              
              <h3 className="text-xl font-bold text-[#263238] mb-2">
                {step.title}
              </h3>
              
              <p className="text-gray-600 mb-6">
                {step.description}
              </p>
              
              {index === 1 ? (
                <button
                  onClick={() => setKpModalOpen(true)}
                  className="inline-block text-[#E53935] font-medium hover:text-red-700 transition-colors"
                >
                  {step.action.text}
                </button>
              ) : (
                <a
                  href={step.action.link}
                  {...(step.action.download ? { download: step.action.download } : {})}
                  className="inline-block text-[#E53935] font-medium hover:text-red-700 transition-colors"
                >
                  {step.action.text}
                </a>
              )}
            </div>
          ))}
        </div>
        
        <div id="questionnaire" className="mt-16 bg-white p-8 rounded-lg shadow-sm">
          <h3 className="text-2xl font-bold text-[#263238] mb-6">
            Загрузите технические условия и заполните опросный лист
          </h3>
          
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1">
              <p className="text-gray-600 mb-4">
                Для точного расчета стоимости и сроков проектирования, пожалуйста, заполните опросный лист и загрузите технические условия от вашей теплоснабжающей организации.
              </p>
              
              <a 
                href={SURVEY_FORM_PDF_HREF}
                download={SURVEY_FORM_PDF_DOWNLOAD_AS}
                className="inline-block bg-[#E53935] hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Скачать опросный лист
              </a>
            </div>
            
            <div className="flex-1">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <p className="text-gray-500 mb-4">
                  Перетащите файлы сюда или нажмите для загрузки
                </p>
                <button className="text-[#E53935] font-medium hover:text-red-700 transition-colors">
                  Выбрать файлы
                </button>
              </div>
            </div>
          </div>
        </div>

        <KpRequestModal isOpen={kpModalOpen} onClose={() => setKpModalOpen(false)} />
      </div>
    </section>
  );
};

export default ProcessSection;