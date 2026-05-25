import React from 'react'
import { LanguageCode } from '../types'
import { LANGUAGES } from '../constants'

interface LanguageSelectorProps {
  value: LanguageCode
  onChange: (lang: LanguageCode) => void
  label?: string
  exclude?: LanguageCode[]
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  value,
  onChange,
  label,
  exclude = [],
}) => {
  const availableLanguages = LANGUAGES.filter(lang => !exclude.includes(lang.code))

  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-gray-700">{label}</label>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as LanguageCode)}
        className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
      >
        {availableLanguages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nativeName} ({lang.name})
          </option>
        ))}
      </select>
    </div>
  )
}
