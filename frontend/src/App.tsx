import React, { useEffect } from 'react';
import Header from './components/Header';
import HeroSection from './components/HeroSection';
import WhyUsSection from './components/WhyUsSection';
import ProcessSection from './components/ProcessSection';
import SampleProjectSection from './components/SampleProjectSection';
import CalculatorSection from './components/CalculatorSection';
import TelegramSupportSection from './components/TelegramSupportSection';
import PartnerFormSection from './components/PartnerFormSection';
import FAQSection from './components/FAQSection';
import Footer from './components/Footer';
import './index.css';

function App() {
  // Set the document title
  useEffect(() => {
    document.title = 'УУТЭ Проект - Проект узла учёта тепловой энергии за 3 дня';
  }, []);

  return (
    <div className="font-[Inter,sans-serif]">
      <Header />
      <HeroSection />
      <WhyUsSection />
      <ProcessSection />
      <SampleProjectSection />
      <CalculatorSection />
      <TelegramSupportSection />
      <PartnerFormSection />
      <FAQSection />
      <Footer />
    </div>
  );
}

export default App;
