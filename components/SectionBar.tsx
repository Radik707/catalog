"use client";

import { useEffect } from "react";

// Пропсы прилипающей полосы разделов
interface SectionBarProps {
  // Список разделов в порядке первого появления
  sections: string[];
  // Текущий активный раздел (подсвечивается синим)
  activeSection: string;
  // Вызывается при клике или при обнаружении раздела scroll-spy'ем
  onSectionChange: (section: string) => void;
}

// Прилипающая полоса разделов под синей шапкой.
// Клик — плавная перемотка к якорю section-{name}.
// Scroll-spy через IntersectionObserver — подсвечивает активный раздел.
export default function SectionBar({
  sections,
  activeSection,
  onSectionChange,
}: SectionBarProps) {
  // Scroll-spy: следим за заголовками разделов через IntersectionObserver.
  // rootMargin "-50% 0px -50% 0px" — срабатывает, когда заголовок в центре экрана.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            // Убираем префикс "section-" чтобы получить имя раздела
            const sectionName = entry.target.id.replace(/^section-/, "");
            onSectionChange(sectionName);
          }
        }
      },
      { rootMargin: "-50% 0px -50% 0px", threshold: 0 }
    );

    // Наблюдаем за якорными заголовками всех разделов
    sections.forEach((s) => {
      const el = document.getElementById(`section-${s}`);
      if (el) observer.observe(el);
    });

    // Обязательная очистка при размонтировании или смене списка разделов
    return () => observer.disconnect();
  }, [sections, onSectionChange]);

  // Обработчик клика: вызываем колбэк и плавно перематываем к якорю
  const handleClick = (section: string) => {
    onSectionChange(section);
    const el = document.getElementById(`section-${section}`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    // Прилипает под синей шапкой (h-12 = 48px), поэтому top-12, а не top-0
    <div className="sticky top-12 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex gap-2 px-4 py-2.5 overflow-x-auto scrollbar-hide">
        {sections.map((section) => (
          <button
            key={section}
            onClick={() => handleClick(section)}
            className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
              activeSection === section
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 active:bg-gray-200"
            }`}
          >
            {section}
          </button>
        ))}
      </div>
    </div>
  );
}
