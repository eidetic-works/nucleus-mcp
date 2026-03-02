// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'Nucleus',
			description: 'Local-First AI Memory for Agentic Workflows',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/eidetic-works/mcp-server-nucleus' },
				{ icon: 'x.com', label: 'Twitter', href: 'https://twitter.com/NucleusMCP' },
			],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', slug: 'guides/example' },
					],
				},
				{
					label: 'Blog',
					autogenerate: { directory: 'blog' },
				},
				{
					label: 'Reference',
					autogenerate: { directory: 'reference' },
				},
			],
		}),
	],
});
