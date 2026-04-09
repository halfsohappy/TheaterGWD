/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./*.html'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono:   ['"Martian Mono"', 'monospace'],
        title:  ['"Playwrite DE Grund"', 'cursive'],
        header: ['"Playwrite IE"', 'cursive'],
      },
      colors: {
        header:      '#DAC7FF',
        'header-dk': '#2a2234',
        accent:      { DEFAULT: '#90849c', hover: '#7a6f8a', dim: 'rgba(144,132,156,0.12)' },
        success:     { DEFAULT: '#4CAF50', dim: 'rgba(76,175,80,0.1)' },
        warning:     { DEFAULT: '#c49030', dim: 'rgba(168,120,32,0.12)' },
        danger:      { DEFAULT: '#a85858', dim: 'rgba(168,88,88,0.12)' },
        send:        '#2A34D5',
        recv:        '#4CAF50',
        bridge:      '#E3BB7F',
        'status-tag':'#936793',
        background:  'hsl(var(--background))',
        foreground:  'hsl(var(--foreground))',
        card:        { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        muted:       { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        border:      'hsl(var(--border))',
        input:       'hsl(var(--input))',
        ring:        'hsl(var(--ring))',
        primary:     { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary:   { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
      },
      borderRadius: {
        lg: '8px',
        md: '6px',
        sm: '4px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({ strategy: 'class' }),
  ],
}

