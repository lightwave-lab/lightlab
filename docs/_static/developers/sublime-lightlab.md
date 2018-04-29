## A decent sublime-project specification for lightlab
Copy-paste this into lightlab/sublime-lightlab.sublime-project
```
{
	"folders":
	[
		{
			"path": "lightlab",
			"folder_exclude_patterns":
			[
				"__pycache__"
			]
		},
		{
			"name": "PyTests",
			"path": "tests",
			"folder_exclude_patterns":
			[
				"__pycache__"
			]
		},
		{
			"name": "Documentation",
			"path": "docs",
			"file_exclude_patterns":
			[
				"*.css",
				"._*"
			]
		},
		{
			"name": "Project",
			"path": ".",
			"folder_exclude_patterns":
			[
				"lightlab",
				"tests",
				"docs",
				"venv",
				"build",
				"lightlab.egg-info",
				"dist",
				"data",
				".pytest_cache"
			],
			"file_exclude_patterns":
			[
				"*.css",
				"._*"
			]
		}
	],
	"settings":
	{
		"tab_size": 4,
		"translate_tabs_to_spaces": true,
		"trim_trailing_white_space_on_save": true
	}
}
```
