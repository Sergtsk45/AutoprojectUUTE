/**
 * @file: siteLegal.ts
 * @description: Единые контактные данные и реквизиты для лэндинга; реквизиты только в подвале, контакты — также в «Свяжитесь с нами».
 * @dependencies: Footer, PartnerFormSection
 * @created: 2026-04-11
 */

export const SITE_CONTACT = {
  address: '675000, г. Благовещенск, ул. Партизанская д.43/2 стр. 2',
  phoneDisplay: '(4162) 66-01-06',
  phoneTel: '+74162660106',
  email: 'noreplay@tsk28.ru',
} as const;

export const SITE_REQUISITES = {
  legalName: 'ООО «Теплосервис-Комплект»',
  innKpp: 'ИНН: 2801131520 / КПП: 280101001',
  ogrn: 'ОГРН: 1082801003944',
  rs: 'Р/с: 40702810803000008544',
  ks: 'К/с: 30101810600000000608',
  bik: 'БИК: 040813608',
  bank: 'ДАЛЬНЕВОСТОЧНЫЙ БАНК ПАО СБЕРБАНК РОССИИ Г. ХАБАРОВСК',
} as const;
