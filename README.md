# MasterKey Gestão Escolar

Aplicação web local simples para controle de turmas, alunos, matrículas e frequência. Os dados ficam no arquivo `masterkey.db`, nesta mesma pasta.

## Instalação e abertura

1. Instale o Python 3 no computador, marcando a opção para adicionar Python ao PATH.
2. Dê dois cliques em `iniciar.bat`. Na primeira abertura, o computador precisa ter internet para instalar Flask, ReportLab e XlsxWriter.
3. Quando a janela indicar que o servidor está ativo, abra `http://127.0.0.1:5000` no navegador.
4. Para encerrar, feche a janela do servidor.

O sistema escuta somente no próprio computador. Outros dispositivos da rede não conseguem acessá-lo.

## Uso rápido

1. Cadastre uma turma e os alunos.
2. Abra a turma e matricule os alunos, informando data e módulo de entrada.
3. Em **Chamadas**, registre data, módulo e número da aula. Marque presença ou falta.
4. Em **Relatórios**, acompanhe a frequência e as aulas concluídas. Exporte o resumo para Excel/PDF, baixe a lista de frequência da turma em PDF e faça backups.
5. A foto do aluno é opcional e pode ser incluída no cadastro ou depois em **Editar**. Use JPG ou PNG de até 3 MB; as fotos ficam na pasta local `student_photos`.

## Correções, busca e alertas

- Em **Alunos**, busque por nome ou turma e use **Editar** para corrigir nome, telefone e observações.
- Em **Turmas**, filtre pelo nome e edite horário ou professor.
- Em **Chamadas**, filtre por turma, módulo e período. Abra uma chamada para corrigir data, módulo ou aula; use **Limpar** para desfazer um registro de presença ou falta.
- A página inicial mostra alunos com duas faltas consecutivas e alunos cuja frequência está abaixo de 70% ou próxima desse limite (depois de pelo menos quatro aulas registradas). **Alertas** mostra a lista completa.
- Relatórios e exportações incluem professor, horário e alertas. Se filtrar por aluno ou turma no relatório, os botões de Excel e PDF exportam o mesmo filtro.
- A **Lista de chamada PDF** é uma folha simples em A4 paisagem, com a turma, professor, horário, alunos e as 27 aulas agrupadas pelos módulos. P/F aparecem onde já há frequência registrada; os demais espaços ficam vazios para preenchimento.

O curso tem Windows (2), E-mail (1), Word (6), Segurança Digital (1), PowerPoint (6), Computação em Nuvem (1), Inteligência Artificial (2) e Excel (8): 27 aulas. O módulo de entrada define as aulas consideradas para conclusão; as chamadas podem ser lançadas em qualquer ordem. A frequência começa na matrícula. A aprovação requer 70% de presença nas aulas registradas e chamadas, e três faltas consecutivas reprovam mesmo em módulos diferentes. A conclusão das aulas é exibida separadamente da aprovação; não há aprovação por módulo.

Faça backups periódicos e guarde-os em outro local. Não apague `masterkey.db` se quiser preservar os cadastros.

## Dados locais

O banco `masterkey.db`, os backups e as fotos dos alunos ficam somente no computador e são ignorados pelo Git. O banco é criado automaticamente quando o aplicativo é iniciado. A chave de sessão também é gerada localmente e não deve ser compartilhada.
