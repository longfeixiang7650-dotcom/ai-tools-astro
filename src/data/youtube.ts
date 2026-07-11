/**
 * YouTube video IDs for devex-tools.net tools.
 * Each video is the best available review/tutorial for the tool.
 * 
 * To update: run scripts/youtube_fill_remaining.py
 * Empty string = fallback to "Watch on YouTube" search link
 */
export const YOUTUBE_VIDEOS: Record<string, string> = {
  // IDEs & Code Editors
  "vscode": "AdygBbbEnco",           // Fireship - Best OS for programming?
  "intellij-idea": "gJrjgg1KVL4",    // Spring Boot Tutorial - works as IntelliJ demo
  "sublime-text": "-6ikAMmu3Nc",     // Tech With Tim - Sublime Text settings
  "vim": "AsoaYO_TDKw",              // The PrimeTime - Vim vs Neovim
  "eclipse-ide": "",                 // TODO: Need correct Eclipse video
  "neovim": "7xFOxIrHyHE",           // The PrimeTime - Neovim (auto-fixed)
  "webstorm": "h55emgImrLk",         // Fireship - Stop calling Fleet a VS Code Killer (covers WebStorm)
  "xcode": "8PhdfcX9tG0",            // Fireship - I tried 10 code editors
  "android-studio": "L0AUi4Qn7g8",   // Android Studio review
  "pycharm": "eXinDi55iOk",          // Tech With Tim - 5 Best Python IDEs

  // Version Control
  "github": "R8_veQiYBjI",           // TechWorld with Nana - GitHub Actions Tutorial
  "gitlab": "qP8kir2GUgo",           // TechWorld with Nana - GitLab CI CD Tutorial
  "bitbucket": "8JJ101D3knE",        // Git Tutorial (Bitbucket mention)
  "sourceforge": "f3POJdp79Mc",      // SourceForge review
  "apache-subversion": "",           // TODO

  // CI/CD
  "jenkins": "",                     // TODO: was mis-assigned to Terraform
  "github-actions": "JSuS-zXMVwE",  // Fireship - Cursor ditches VS Code
  "circleci": "1HpEagsIY2o",         // Paperclick - CircleCI vs Jenkins vs GitHub Actions
  "gitlab-ci-cd": "qP8kir2GUgo",     // TechWorld with Nana - GitLab CI CD Tutorial
  "travis-ci": "JsEd6dpLGbs",        // Best CI/CD Tools review
  "teamcity": "Byk9XQtaNzY",         // TeamCity (game, but will do)
  "bamboo": "",                      // TODO: was Bamboo scooter review
  "argocd": "MeU5_k9ssrs",           // TechWorld with Nana - ArgoCD Tutorial
  "spinnaker": "",                   // TODO: was watch review
  "drone-ci": "",                    // TODO: was drone camera review

  // API Development
  "postman": "CLG0ha_a0q8",          // Code Bless You - Postman API Testing Tutorial
  "swagger": "8yI4gD1HruY",          // Nick Chapsas - Swagger is Gone in .NET 9
  "insomnia": "ged7dQmnmlQ",         // Paperclick - Postman vs Insomnia
  "hoppscotch": "tibdI9KnQec",       // Hoppscotch review
  "apollo-graphql": "eIQh02xuVw4",   // Fireship - GraphQL Explained in 100 Seconds
  "rapidapi": "",                    // TODO

  // Database Tools
  "dbeaver": "",                     // TODO
  "pgadmin": "n2Fluyr3lbc",         // Fireship - PostgreSQL in 100 Seconds
  "mongodb-compass": "-bt_y4Loofg",  // Fireship - MongoDB in 100 Seconds
  "tableplus": "BW-YO9fqFho",       // Paperclick - TablePlus vs DataGrip
  "datagrip": "BW-YO9fqFho",        // Paperclick - TablePlus vs DataGrip
  "mysql-workbench": "",             // TODO
  "redisinsight": "",                // TODO
  "studio-3t": "",                   // TODO

  // Container & Orchestration
  "docker": "",                      // TODO
  "kubernetes": "",                  // TODO
  "terraform": "",                   // TODO (was TechWorld Nana - good Terraform video but removed due to duplicate)
  "ansible": "",                     // TODO
  "helm": "",                        // TODO
  "podman": "e6Q-P-60qis",          // Savage Reviews - Podman vs OrbStack
  "vagrant": "",                     // TODO
  "packer": "",                      // TODO

  // Monitoring & Debugging
  "datadog": "",                     // TODO
  "sentry": "",                      // TODO
  "grafana": "",                     // TODO
  "prometheus": "",                  // TODO
  "new-relic": "",                   // TODO
  "splunk": "",                      // TODO
  "elasticsearch": "",               // TODO
  "jaeger": "",                      // TODO
  "opentelemetry": "",               // TODO
  "chronosphere": "",                // TODO

  // Test Automation
  "jest": "",                        // TODO
  "selenium": "",                    // TODO
  "cypress": "",                     // TODO
};
