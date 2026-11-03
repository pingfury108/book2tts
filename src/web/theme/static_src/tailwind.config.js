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
    /*
     * 封面调色板：这些 class 由 cover_gradient 过滤器动态拼接，
     * Tailwind JIT 扫不到源码，必须 safelist（对应 workbench/templatetags/custom_filters.py）。
     */
    safelist: [
        'from-violet-500', 'to-violet-700',
        'from-sky-500', 'to-sky-700',
        'from-emerald-500', 'to-emerald-700',
        'from-amber-500', 'to-amber-600',
        'from-rose-500', 'to-rose-700',
        'from-indigo-500', 'to-indigo-700',
        'bg-gradient-to-br',
    ],
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
                /* V2 设计系统（designs/b2t-ui-v2/S2+D1 画板）：
                 * - ink 深紫黑替代纯黑，暖纸底色
                 * - primary 加深一档 #6d28d9：唯一主 CTA
                 * - accent #e65302：播放键专属，全页唯一暖色焦点
                 * - 暗色：深紫墨底，brand/accent 提亮保对比
                 * - rounded-box/btn 统一全局圆角两档（16/12.8px） */
                light: {
                    primary: "#6d28d9",
                    "primary-content": "#ffffff",
                    secondary: "#4d4956",
                    "secondary-content": "#f6f5f2",
                    accent: "#e65302",
                    "accent-content": "#ffffff",
                    neutral: "#2a2632",
                    "neutral-content": "#f6f5f2",
                    "base-100": "#ffffff",
                    "base-200": "#f6f5f2",
                    "base-300": "#e5e3e8",
                    "base-content": "#191622",
                    info: "#0284c7",
                    "info-content": "#ffffff",
                    success: "#1a7f4b",
                    "success-content": "#ffffff",
                    warning: "#b45309",
                    "warning-content": "#ffffff",
                    error: "#d13438",
                    "error-content": "#ffffff",
                    "rounded-box": "1rem",
                    "rounded-btn": "0.8rem",
                    "rounded-badge": "0.7rem",
                },
                dark: {
                    primary: "#8b5cf6",
                    "primary-content": "#ffffff",
                    secondary: "#b6b1c4",
                    "secondary-content": "#191622",
                    accent: "#f97316",
                    "accent-content": "#ffffff",
                    neutral: "#e5e3e8",
                    "neutral-content": "#191622",
                    "base-100": "#1d1a26",
                    "base-200": "#14121a",
                    "base-300": "#34303e",
                    "base-content": "#ece9f4",
                    info: "#38bdf8",
                    "info-content": "#191622",
                    success: "#4ade80",
                    "success-content": "#191622",
                    warning: "#fbbf24",
                    "warning-content": "#191622",
                    error: "#f87171",
                    "error-content": "#191622",
                    "rounded-box": "1rem",
                    "rounded-btn": "0.8rem",
                    "rounded-badge": "0.7rem",
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
