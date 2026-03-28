"use client";

interface CategoryFilterProps {
  groups: string[];
  activeGroup: string;
  onSelect: (group: string) => void;
}

export default function CategoryFilter({
  groups,
  activeGroup,
  onSelect,
}: CategoryFilterProps) {
  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex gap-2 px-4 py-2.5 overflow-x-auto scrollbar-hide">
        <button
          onClick={() => onSelect("")}
          className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors ${
            activeGroup === ""
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-600 active:bg-gray-200"
          }`}
        >
          Все
        </button>
        {groups.map((group) => (
          <button
            key={group}
            onClick={() => onSelect(group)}
            className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
              activeGroup === group
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 active:bg-gray-200"
            }`}
          >
            {group}
          </button>
        ))}
      </div>
    </div>
  );
}
