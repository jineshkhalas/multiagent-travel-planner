import React from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Plane, 
  CloudSun, 
  Building2, 
  Calendar, 
  Sunrise, 
  Sun, 
  Sunset, 
  Ticket, 
  Utensils, 
  Car, 
  Navigation, 
  MapPin, 
  Clock, 
  Sparkles,
  Info
} from 'lucide-react';

function stripEmojis(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F100}-\u{1F1FF}\u{1F200}-\u{1F2FF}\u{1FA70}-\u{1FAFF}]/gu, '')
    .trim();
}

export default function ItineraryDisplay({ content }) {
  if (!content) return null;

  const cleanContent = stripEmojis(content);

  const MarkdownComponents = {
    h1: ({ children }) => {
      const text = String(children);
      return (
        <div className="flex items-center flex-wrap gap-2 mt-4 sm:mt-5 mb-2.5 sm:mb-3 pb-1.5 sm:pb-2 border-b border-gray-200 dark:border-gray-800 text-gray-900 dark:text-gray-100 font-bold text-base sm:text-lg">
          <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400 shrink-0" />
          <span className="break-words">{text}</span>
        </div>
      );
    },

    h2: ({ children }) => {
      const text = String(children);
      let icon = <MapPin className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600 dark:text-blue-400" />;
      let badge = null;

      if (/flight|transit|travel/i.test(text)) {
        icon = <Plane className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600 dark:text-blue-400" />;
        badge = "Transit Details";
      } else if (/weather|climate|forecast/i.test(text)) {
        icon = <CloudSun className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-500 dark:text-amber-400" />;
        badge = "Live Forecast";
      } else if (/hotel|accommodation|stay|resort/i.test(text)) {
        icon = <Building2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-600 dark:text-emerald-400" />;
        badge = "Stays & Tariffs";
      } else if (/itinerary|day|schedule/i.test(text)) {
        icon = <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-600 dark:text-indigo-400" />;
        badge = "Day-by-Day";
      }

      return (
        <div className="flex items-center justify-between flex-wrap gap-1.5 mt-4 sm:mt-5 mb-2 sm:mb-2.5 pt-2 sm:pt-3 pb-1 border-b border-gray-100 dark:border-gray-800/80">
          <div className="flex items-center gap-1.5 sm:gap-2 text-gray-900 dark:text-gray-100 font-bold text-xs sm:text-sm tracking-tight min-w-0">
            <div className="p-1 sm:p-1.5 rounded-lg bg-gray-100/80 dark:bg-gray-800 text-gray-700 dark:text-gray-300 shrink-0">
              {icon}
            </div>
            <span className="break-words">{text}</span>
          </div>
          {badge && (
            <span className="text-[9px] sm:text-[10px] font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 sm:px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0">
              {badge}
            </span>
          )}
        </div>
      );
    },

    h3: ({ children }) => {
      const text = String(children);
      let icon = <MapPin className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600 dark:text-blue-400" />;
      let badge = null;

      if (/flight|transit|travel/i.test(text)) {
        icon = <Plane className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-600 dark:text-blue-400" />;
        badge = "Transit";
      } else if (/weather|climate|forecast/i.test(text)) {
        icon = <CloudSun className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-500 dark:text-amber-400" />;
        badge = "Live Weather";
      } else if (/hotel|accommodation|stay|resort/i.test(text)) {
        icon = <Building2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-600 dark:text-emerald-400" />;
        badge = "Hotels";
      } else if (/itinerary|day|schedule/i.test(text)) {
        icon = <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-600 dark:text-indigo-400" />;
        badge = "Itinerary";
      }

      return (
        <div className="flex items-center justify-between flex-wrap gap-1.5 mt-3 sm:mt-4 mb-1.5 sm:mb-2 pb-1 border-b border-gray-100 dark:border-gray-800/80">
          <div className="flex items-center gap-1.5 sm:gap-2 text-gray-800 dark:text-gray-200 font-bold text-xs sm:text-sm min-w-0">
            <div className="p-1 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shrink-0">
              {icon}
            </div>
            <span className="break-words">{text}</span>
          </div>
          {badge && (
            <span className="text-[9px] sm:text-[10px] font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/60 px-1.5 sm:px-2 py-0.5 rounded-full shrink-0">
              {badge}
            </span>
          )}
        </div>
      );
    },

    p: ({ children }) => (
      <div className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm leading-relaxed mb-2 break-words">
        {children}
      </div>
    ),

    li: ({ children }) => (
      <li className="text-gray-700 dark:text-gray-300 text-xs sm:text-sm mb-1.5 leading-relaxed pl-1 break-words">
        {children}
      </li>
    ),

    strong: ({ children }) => {
      const text = String(children).trim();

      if (/^morning$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-bold text-amber-800 dark:text-amber-300 bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 px-1.5 sm:px-2 py-0.5 rounded-md text-[10px] sm:text-xs mr-1 my-0.5 shadow-xs shrink-0">
            <Sunrise className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>Morning</span>
          </span>
        );
      }

      if (/^afternoon$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-bold text-yellow-800 dark:text-yellow-300 bg-yellow-50/90 dark:bg-yellow-950/40 border border-yellow-200 dark:border-yellow-800/60 px-1.5 sm:px-2 py-0.5 rounded-md text-[10px] sm:text-xs mr-1 my-0.5 shadow-xs shrink-0">
            <Sun className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
            <span>Afternoon</span>
          </span>
        );
      }

      if (/^evening$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-bold text-indigo-800 dark:text-indigo-300 bg-indigo-50/90 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60 px-1.5 sm:px-2 py-0.5 rounded-md text-[10px] sm:text-xs mr-1 my-0.5 shadow-xs shrink-0">
            <Sunset className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
            <span>Evening</span>
          </span>
        );
      }

      if (/^day\s*\d+/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-bold text-blue-900 dark:text-blue-200 bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800/60 px-2 py-0.5 sm:py-1 rounded-lg text-[10px] sm:text-xs mr-1.5 my-0.5 shadow-xs shrink-0">
            <Calendar className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
            <span>{text}</span>
          </span>
        );
      }

      return <strong className="font-semibold text-gray-900 dark:text-gray-100 break-words">{children}</strong>;
    },

    ul: ({ children }) => (
      <ul className="space-y-1 sm:space-y-1.5 my-2 pl-3 sm:pl-4 list-disc marker:text-blue-500 dark:marker:text-blue-400 text-xs sm:text-sm">
        {children}
      </ul>
    ),

    ol: ({ children }) => (
      <ol className="space-y-1 sm:space-y-1.5 my-2 pl-3 sm:pl-4 list-decimal marker:font-semibold marker:text-blue-600 dark:marker:text-blue-400 text-xs sm:text-sm">
        {children}
      </ol>
    ),

    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-950/30 p-2 sm:p-3 my-2 rounded-r-lg text-[11px] sm:text-xs text-gray-700 dark:text-gray-300 italic flex gap-1.5 sm:gap-2 items-start">
        <Info className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-500 dark:text-blue-400 shrink-0 mt-0.5" />
        <div className="break-words min-w-0">{children}</div>
      </blockquote>
    ),

    code: ({ children }) => (
      <code className="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-[10px] sm:text-xs font-mono break-all">
        {children}
      </code>
    ),

    pre: ({ children }) => (
      <pre className="p-2 sm:p-3 my-2 rounded-xl bg-gray-900 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 text-gray-100 overflow-x-auto text-[10px] sm:text-xs font-mono max-w-full">
        {children}
      </pre>
    ),

    table: ({ children }) => (
      <div className="overflow-x-auto my-2 sm:my-3 max-w-full">
        <table className="w-full border-collapse text-[10px] sm:text-xs border border-gray-200 dark:border-gray-700">
          {children}
        </table>
      </div>
    ),

    th: ({ children }) => (
      <th className="border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-1.5 sm:p-2 text-left font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">
        {children}
      </th>
    ),

    td: ({ children }) => (
      <td className="border border-gray-200 dark:border-gray-700 p-1.5 sm:p-2 text-gray-700 dark:text-gray-300">
        {children}
      </td>
    ),

    hr: () => (
      <hr className="border-t border-gray-200 dark:border-gray-800 my-3 sm:my-4" />
    )
  };

  return (
    <div className="w-full max-w-full overflow-hidden">
      <ReactMarkdown components={MarkdownComponents}>
        {cleanContent}
      </ReactMarkdown>
    </div>
  );
}
