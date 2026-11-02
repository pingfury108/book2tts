/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        extend: {},
    },
    daisyui: {
        /*
         * B2T 设计系统 token（designs/b2t-ui-redesign/F 画板）：
         * - primary 品牌紫：唯一主 CTA
         * - accent 暖橙：播放键专属，全页唯一暖色焦点
         * - base-200 为页面底色（暖白/暖黑）
         * 按名覆盖内置 light/dark，主题切换 JS 无需改动。
         */
        themes: [
            {
                light: {
                    primary: "#7c3aed",
                    "primary-content": "#ffffff",
                    secondary: "#57534e",
                    "secondary-content": "#fafaf9",
                    accent: "#ea580c",
                    "accent-content": "#ffffff",
                    neutral: "#292524",
                    "neutral-content": "#fafaf9",
                    "base-100": "#ffffff",
                    "base-200": "#faf9f7",
                    "base-300": "#e7e5e4",
                    "base-content": "#1c1917",
                    info: "#0284c7",
                    "info-content": "#ffffff",
                    success: "#15803d",
                    "success-content": "#ffffff",
                    warning: "#b45309",
                    "warning-content": "#ffffff",
                    error: "#dc2626",
                    "error-content": "#ffffff",
                },
                dark: {
                    primary: "#8b5cf6",
                    "primary-content": "#ffffff",
                    secondary: "#a8a29e",
                    "secondary-content": "#1c1917",
                    accent: "#f97316",
                    "accent-content": "#ffffff",
                    neutral: "#e7e5e4",
                    "neutral-content": "#1c1917",
                    "base-100": "#262524",
                    "base-200": "#1c1b1a",
                    "base-300": "#393735",
                    "base-content": "#e7e5e4",
                    info: "#38bdf8",
                    "info-content": "#1c1917",
                    success: "#4ade80",
                    "success-content": "#1c1917",
                    warning: "#fbbf24",
                    "warning-content": "#1c1917",
                    error: "#f87171",
                    "error-content": "#1c1917",
                },
            },
        ],
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
	require("daisyui"),
    ],
}
