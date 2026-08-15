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
  Info,
  Train,
  Bus,
  Star,
  DollarSign
} from 'lucide-react';

function stripEmojis(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F100}-\u{1F1FF}\u{1F200}-\u{1F2FF}\u{1FA70}-\u{1FAFF}]/gu, '')
    .trim();
}

function extractText(node) {
  if (node === null || node === undefined) return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (React.isValidElement(node) && node.props && node.props.children) {
    return extractText(node.props.children);
  }
  return '';
}

export default function ItineraryDisplay({ content }) {
  if (!content) return null;

  const cleanContent = stripEmojis(content);

  const MarkdownComponents = {
    h1: ({ children }) => {
      return (
        <div className="flex items-center flex-wrap gap-2.5 mt-6 mb-4 pb-2 border-b border-gray-200 dark:border-gray-800 text-gray-900 dark:text-gray-100 font-bold text-base sm:text-lg font-heading tracking-[0.035em] [word-spacing:0.08em]">
          <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
          <span className="break-words">{children}</span>
        </div>
      );
    },

    h2: ({ children }) => {
      const text = extractText(children);
      let icon = <MapPin className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
      let badge = null;

      if (/flight|transit|travel/i.test(text)) {
        icon = <Plane className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
        badge = "Transit Details";
      } else if (/weather|climate|forecast/i.test(text)) {
        icon = <CloudSun className="w-4 h-4 text-amber-500 dark:text-amber-400" />;
        badge = "Live Forecast";
      } else if (/hotel|accommodation|stay|resort/i.test(text)) {
        icon = <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />;
        badge = "Stays & Tariffs";
      } else if (/itinerary|day|schedule/i.test(text)) {
        icon = <Calendar className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />;
        badge = "Day-by-Day";
      }

      return (
        <div className="flex items-center justify-between flex-wrap gap-2 mt-7 mb-3.5 pt-3.5 pb-2 border-b border-gray-200/80 dark:border-gray-800 font-heading tracking-[0.035em] [word-spacing:0.08em]">
          <div className="flex items-center gap-2 text-gray-900 dark:text-gray-100 font-bold text-sm sm:text-base tracking-tight min-w-0">
            <div className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 shrink-0 shadow-xs">
              {icon}
            </div>
            <span className="break-words">{children}</span>
          </div>
          {badge && (
            <span className="text-[10px] sm:text-xs font-semibold text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2.5 py-0.5 rounded-full uppercase tracking-wider shrink-0">
              {badge}
            </span>
          )}
        </div>
      );
    },

    h3: ({ children }) => {
      const text = extractText(children);
      let icon = <MapPin className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
      let badge = null;

      if (/flight|transit|travel/i.test(text)) {
        icon = <Plane className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
        badge = "Transit Options";
      } else if (/weather|climate|forecast/i.test(text)) {
        icon = <CloudSun className="w-4 h-4 text-amber-500 dark:text-amber-400" />;
        badge = "Live Weather";
      } else if (/hotel|accommodation|stay|resort/i.test(text)) {
        icon = <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />;
        badge = "Accommodations";
      } else if (/itinerary|day|schedule/i.test(text)) {
        icon = <Calendar className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />;
        badge = "Day-by-Day Plan";
      }

      return (
        <div className="flex items-center justify-between flex-wrap gap-2 mt-6 mb-3 pb-2 border-b border-gray-200/90 dark:border-gray-800 font-heading tracking-[0.035em] [word-spacing:0.08em]">
          <div className="flex items-center gap-2 text-gray-900 dark:text-gray-100 font-bold text-sm sm:text-base min-w-0">
            <div className="p-1.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shrink-0">
              {icon}
            </div>
            <span className="break-words">{children}</span>
          </div>
          {badge && (
            <span className="text-[10px] sm:text-xs font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/60 px-2 py-0.5 rounded-full shrink-0">
              {badge}
            </span>
          )}
        </div>
      );
    },

    h4: ({ children }) => {
      const text = extractText(children);
      let icon = <Navigation className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400 shrink-0" />;

      if (/flight/i.test(text)) {
        icon = <Plane className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
      } else if (/train/i.test(text)) {
        icon = <Train className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
      } else if (/road|cab|drive|transit|bus/i.test(text)) {
        icon = <Car className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      } else if (/luxury|5-star|7-star/i.test(text)) {
        icon = <Sparkles className="w-3.5 h-3.5 text-purple-500 shrink-0" />;
      } else if (/3-star|4-star|premium/i.test(text)) {
        icon = <Building2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
      } else if (/budget|cheap/i.test(text)) {
        icon = <Ticket className="w-3.5 h-3.5 text-green-500 shrink-0" />;
      } else if (/day\s*\d+/i.test(text)) {
        icon = <Calendar className="w-3.5 h-3.5 text-indigo-500 shrink-0" />;
      } else if (/weather|climate/i.test(text)) {
        icon = <CloudSun className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      }

      return (
        <div className="flex items-center gap-2 mt-5 mb-2.5 text-gray-900 dark:text-gray-100 font-semibold text-xs sm:text-sm font-heading tracking-[0.035em] [word-spacing:0.08em]">
          {icon}
          <span>{children}</span>
        </div>
      );
    },

    p: ({ children }) => (
      <div className="text-gray-700 dark:text-gray-300 text-[14px] sm:text-[15px] leading-[1.85] mb-3.5 break-words font-normal tracking-[0.028em] [word-spacing:0.08em]">
        {children}
      </div>
    ),

    li: ({ children }) => (
      <li className="text-gray-700 dark:text-gray-300 text-[14px] sm:text-[15px] mb-3 leading-[1.85] pl-1 break-words font-normal tracking-[0.028em] [word-spacing:0.08em]">
        {children}
      </li>
    ),

    strong: ({ children }) => {
      const text = extractText(children).trim();

      if (/^morning$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1.5 font-bold text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800/60 px-2 py-0.5 rounded-md text-[11px] sm:text-xs mr-1.5 my-1 shadow-xs shrink-0 tracking-normal [word-spacing:normal]">
            <Sunrise className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>Morning</span>
          </span>
        );
      }

      if (/^afternoon$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1.5 font-bold text-yellow-800 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-950/50 border border-yellow-200 dark:border-yellow-800/60 px-2 py-0.5 rounded-md text-[11px] sm:text-xs mr-1.5 my-1 shadow-xs shrink-0 tracking-normal [word-spacing:normal]">
            <Sun className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
            <span>Afternoon</span>
          </span>
        );
      }

      if (/^evening$/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1.5 font-bold text-indigo-800 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 px-2 py-0.5 rounded-md text-[11px] sm:text-xs mr-1.5 my-1 shadow-xs shrink-0 tracking-normal [word-spacing:normal]">
            <Sunset className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
            <span>Evening</span>
          </span>
        );
      }

      if (/^day\s*\d+/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1.5 font-bold text-blue-900 dark:text-blue-200 bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800/60 px-2.5 py-1 rounded-lg text-xs mr-2 my-1 shadow-xs shrink-0 font-heading tracking-normal [word-spacing:normal]">
            <Calendar className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
            <span>{text}</span>
          </span>
        );
      }

      if (/^(cab|taxi|car|rental car)/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-amber-800 dark:text-amber-300 bg-amber-50/90 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800/60 px-1.5 py-0.5 rounded text-[11px] sm:text-xs mr-1 tracking-normal [word-spacing:normal]">
            <Car className="w-3 h-3 text-amber-500" />
            <span>{text}</span>
          </span>
        );
      }

      if (/^(bus|state transport|volvo)/i.test(text)) {
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-blue-800 dark:text-blue-300 bg-blue-50/90 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800/60 px-1.5 py-0.5 rounded text-[11px] sm:text-xs mr-1 tracking-normal [word-spacing:normal]">
            <Bus className="w-3 h-3 text-blue-500" />
            <span>{text}</span>
          </span>
        );
      }

      return <strong className="font-semibold text-gray-900 dark:text-gray-100 break-words tracking-[0.025em]">{children}</strong>;
    },

    ul: ({ children }) => (
      <ul className="space-y-3.5 my-3 pl-4 sm:pl-5 list-disc marker:text-blue-500 dark:marker:text-blue-400 text-[14px] sm:text-[15px]">
        {children}
      </ul>
    ),

    ol: ({ children }) => (
      <ol className="space-y-3.5 my-3 pl-4 sm:pl-5 list-decimal marker:font-semibold marker:text-blue-600 dark:marker:text-blue-400 text-[14px] sm:text-[15px]">
        {children}
      </ol>
    ),

    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 dark:border-blue-400 bg-blue-50/60 dark:bg-blue-950/40 p-3 sm:p-4 my-3.5 rounded-r-lg text-xs sm:text-sm text-gray-700 dark:text-gray-300 italic flex gap-2 items-start leading-[1.8] tracking-[0.025em] [word-spacing:0.06em]">
        <Info className="w-4 h-4 text-blue-500 dark:text-blue-400 shrink-0 mt-0.5" />
        <div className="break-words min-w-0">{children}</div>
      </blockquote>
    ),

    code: ({ children }) => (
      <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-xs font-mono break-all">
        {children}
      </code>
    ),

    pre: ({ children }) => (
      <pre className="p-3 my-3 rounded-xl bg-gray-900 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 text-gray-100 overflow-x-auto text-xs font-mono max-w-full leading-normal">
        {children}
      </pre>
    ),

    table: ({ children }) => (
      <div className="overflow-x-auto my-3 max-w-full">
        <table className="w-full border-collapse text-xs border border-gray-200 dark:border-gray-700">
          {children}
        </table>
      </div>
    ),

    th: ({ children }) => (
      <th className="border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-2 text-left font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap">
        {children}
      </th>
    ),

    td: ({ children }) => (
      <td className="border border-gray-200 dark:border-gray-700 p-2 text-gray-700 dark:text-gray-300">
        {children}
      </td>
    ),

    hr: () => (
      <hr className="border-t border-gray-200 dark:border-gray-800 my-4" />
    )
  };

  return (
    <div className="w-full max-w-full overflow-hidden font-sans itinerary-content">
      <ReactMarkdown components={MarkdownComponents}>
        {cleanContent}
      </ReactMarkdown>
    </div>
  );
}
