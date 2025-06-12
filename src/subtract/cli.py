"""
Command-line interface for SubTract pipeline.

This module provides a rich CLI for running the SubTract pipeline
with support for BIDS datasets and comprehensive progress tracking.
"""

import sys
from pathlib import Path
from typing import List, Optional
import logging

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.logging import RichHandler
from rich.panel import Panel

from .config.settings import SubtractConfig
from .core.subject_manager import SubjectManager
from .core.pipeline_runner import PipelineRunner


console = Console()


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    return logging.getLogger("subtract")


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """SubTract: Subcortical Tractography Pipeline"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['logger'] = setup_logging(verbose)


@cli.command()
@click.argument('bids_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), 
              help='Output directory for pipeline results (default: BIDS_DIR/derivatives/subtract)')
@click.option('--participant-label', '-p', multiple=True, 
              help='One or more participant labels to process (e.g., sub-001 sub-002)')
@click.option('--session-id', '-s', multiple=True,
              help='One or more session IDs to process (e.g., ses-baseline ses-followup)')
@click.option('--steps', multiple=True, 
              default=['copy_data', 'denoise', 'topup', 'eddy', 'mdt', 'mrtrix_prep', 'tractography', 'sift2', 'roi_registration', 'connectome'],
              help='Pipeline steps to run (comma-separated or multiple --steps flags). Available steps:\n'
                   '  copy_data: Copy and organize BIDS data\n'
                   '  denoise: DWI denoising using MP-PCA\n'
                   '  topup: Field map estimation and correction\n'
                   '  eddy: Eddy current and motion correction\n'
                   '  mdt: Microstructure modeling (NODDI, DTI)\n'
                   '  mrtrix_prep: MRtrix3 preprocessing (response, FOD)\n'
                   '  tractography: Generate 1M tracks per hemisphere\n'
                   '  sift2: Track filtering and optimization\n'
                   '  roi_registration: ROI registration to subject space\n'
                   '  connectome: Generate connectivity matrices')
@click.option('--n-threads', '-t', type=int, default=24,
              help='Number of CPU threads to use for parallel processing')
@click.option('--force', is_flag=True,
              help='Force overwrite existing outputs (use with caution)')
@click.option('--parallel', is_flag=True,
              help='Process multiple subjects in parallel')
@click.option('--dry-run', is_flag=True,
              help='Show what would be processed without running the pipeline')
@click.pass_context
def run(ctx, bids_dir, output_dir, participant_label, session_id, steps, 
        n_threads, force, parallel, dry_run):
    """Run the SubTract pipeline on a BIDS dataset.
    
    This command processes diffusion MRI data through a complete pipeline
    optimized for subcortical tractography. The pipeline includes preprocessing,
    tractography, and connectomics analysis.
    
    Example:
        subtract run /path/to/bids/dataset --participant-label sub-001 --steps tractography,sift2
    """
    
    logger = ctx.obj['logger']
    
    # Create configuration
    if output_dir is None:
        output_dir = bids_dir.parent / "derivatives" / "subtract"
    
    config = SubtractConfig.from_bids_dataset(bids_dir)
    config.paths.analysis_dir = output_dir
    config.paths.result_dir = output_dir / "results"
    config.processing.n_threads = n_threads
    config.processing.force_overwrite = force
    config.steps_to_run = list(steps)
    
    # Filter subjects if specified
    if participant_label:
        subject_filter = "|".join(participant_label)
        config.subject_filter = f"^({subject_filter})$"
    
    # Filter sessions if specified
    if session_id:
        config.bids.sessions = list(session_id)
    
    # Validate configuration
    try:
        config.validate_paths()
        if config.bids.validate_bids:
            config.validate_bids_structure()
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        sys.exit(1)
    
    # Initialize managers
    subject_manager = SubjectManager(config, logger)
    pipeline_runner = PipelineRunner(config, logger)
    
    # Discover subjects
    subjects = subject_manager.discover_subjects()
    
    if not subjects:
        console.print("[yellow]No subjects found to process[/yellow]")
        return
    
    # Show processing plan
    console.print(Panel.fit(
        f"[bold]SubTract Pipeline[/bold]\n"
        f"BIDS Directory: {bids_dir}\n"
        f"Output Directory: {output_dir}\n"
        f"Subjects: {len(subjects)}\n"
        f"Steps: {', '.join(steps)}\n"
        f"Threads: {n_threads}\n"
        f"Parallel: {parallel}",
        title="Processing Plan"
    ))
    
    if dry_run:
        _show_processing_plan(subject_manager, subjects)
        return
    
    # Run pipeline
    if parallel:
        console.print("[blue]Running subjects in parallel...[/blue]")
        results = pipeline_runner.run_multiple_subjects(subjects, parallel=True)
    else:
        console.print("[blue]Running subjects sequentially...[/blue]")
        results = pipeline_runner.run_multiple_subjects(subjects, parallel=False)
    
    # Show summary
    summary = pipeline_runner.get_pipeline_summary(results)
    _show_pipeline_summary(summary)


@cli.command()
@click.argument('bids_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--participant-label', '-p', multiple=True,
              help='Participant label(s) to validate')
@click.option('--session-id', '-s', multiple=True,
              help='Session ID(s) to validate')
@click.pass_context
def validate(ctx, bids_dir, participant_label, session_id):
    """Validate BIDS dataset for SubTract processing."""
    
    logger = ctx.obj['logger']
    
    # Create configuration
    config = SubtractConfig.from_bids_dataset(bids_dir)
    
    # Filter subjects if specified
    if participant_label:
        subject_filter = "|".join(participant_label)
        config.subject_filter = f"^({subject_filter})$"
    
    # Filter sessions if specified
    if session_id:
        config.bids.sessions = list(session_id)
    
    # Initialize subject manager
    subject_manager = SubjectManager(config, logger)
    
    # Discover and validate subjects
    subjects = subject_manager.discover_subjects()
    
    if not subjects:
        console.print("[yellow]No subjects found[/yellow]")
        return
    
    console.print(f"[blue]Validating {len(subjects)} subjects...[/blue]")
    
    # Create validation table
    table = Table(title="BIDS Validation Results")
    table.add_column("Subject", style="cyan")
    table.add_column("Session", style="magenta")
    table.add_column("DWI Files", justify="right")
    table.add_column("Anat Files", justify="right")
    table.add_column("Dual PE", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Issues")
    
    total_valid = 0
    
    for subject_id in subjects:
        sessions = subject_manager.get_subject_sessions(subject_id)
        
        if sessions:
            for session_id in sessions:
                validation = subject_manager.validate_subject(subject_id, session_id)
                _add_validation_row(table, validation)
                if validation['valid']:
                    total_valid += 1
        else:
            validation = subject_manager.validate_subject(subject_id)
            _add_validation_row(table, validation)
            if validation['valid']:
                total_valid += 1
    
    console.print(table)
    console.print(f"\n[green]{total_valid} valid subjects/sessions found[/green]")


@cli.command()
@click.argument('bids_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Output directory (default: BIDS_DIR/derivatives/subtract)')
@click.pass_context
def status(ctx, bids_dir, output_dir):
    """Show processing status for subjects."""
    
    logger = ctx.obj['logger']
    
    # Create configuration
    if output_dir is None:
        output_dir = bids_dir.parent / "derivatives" / "subtract"
    
    config = SubtractConfig.from_bids_dataset(bids_dir)
    config.paths.analysis_dir = output_dir
    
    # Initialize subject manager
    subject_manager = SubjectManager(config, logger)
    
    # Get subjects and summary
    subjects = subject_manager.discover_subjects()
    summary = subject_manager.get_subjects_summary(subjects)
    
    # Show summary
    console.print(Panel.fit(
        f"[bold]Processing Status[/bold]\n"
        f"Total Subjects: {summary['total_subjects']}\n"
        f"Valid Subjects: {summary['valid_subjects']}\n"
        f"BIDS Compliant: {summary['is_bids']}\n"
        f"With Sessions: {summary.get('subjects_with_sessions', 0)}\n"
        f"Dual Phase Encoding: {summary['subjects_with_dual_encoding']}",
        title="Dataset Summary"
    ))
    
    # Show step completion
    if summary['processing_status']:
        step_table = Table(title="Step Completion")
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Completed", justify="right")
        step_table.add_column("Percentage", justify="right")
        
        for step, count in summary['processing_status'].items():
            percentage = (count / summary['total_subjects']) * 100 if summary['total_subjects'] > 0 else 0
            step_table.add_row(
                step,
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(step_table)


@cli.command()
@click.argument('bids_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), default='subtract_config.yaml',
              help='Output configuration file path')
@click.pass_context
def init_config(ctx, bids_dir, output):
    """Create a configuration file for a BIDS dataset."""
    
    logger = ctx.obj['logger']
    
    try:
        # Create configuration from BIDS dataset
        config = SubtractConfig.from_bids_dataset(bids_dir)
        
        # Save to file
        config.save_to_file(output)
        
        console.print(f"[green]Configuration saved to: {output}[/green]")
        console.print("[yellow]Please edit the configuration file to customize settings.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Failed to create configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(path_type=Path))
@click.pass_context
def run_config(ctx, config_file):
    """Run pipeline using a configuration file."""
    
    logger = ctx.obj['logger']
    
    try:
        config = SubtractConfig.from_file(config_file)
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        sys.exit(1)
    
    # Validate configuration
    try:
        config.validate_paths()
        if config.bids.validate_bids:
            config.validate_bids_structure()
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        sys.exit(1)
    
    # Initialize managers
    subject_manager = SubjectManager(config, logger)
    pipeline_runner = PipelineRunner(config, logger)
    
    # Discover subjects
    subjects = subject_manager.discover_subjects()
    
    if not subjects:
        console.print("[yellow]No subjects found to process[/yellow]")
        return
    
    # Run pipeline
    console.print(f"[blue]Processing {len(subjects)} subjects...[/blue]")
    results = pipeline_runner.run_multiple_subjects(subjects)
    
    # Show summary
    summary = pipeline_runner.get_pipeline_summary(results)
    _show_pipeline_summary(summary)


def _show_processing_plan(subject_manager: SubjectManager, subjects: List[str]):
    """Show what would be processed in dry-run mode."""
    table = Table(title="Processing Plan (Dry Run)")
    table.add_column("Subject", style="cyan")
    table.add_column("Session", style="magenta")
    table.add_column("DWI Files", justify="right")
    table.add_column("Status")
    
    for subject_id in subjects:
        sessions = subject_manager.get_subject_sessions(subject_id)
        
        if sessions:
            for session_id in sessions:
                validation = subject_manager.validate_subject(subject_id, session_id)
                status = "✓ Ready" if validation['valid'] else "✗ Issues"
                table.add_row(
                    subject_id,
                    session_id,
                    str(validation['data_summary'].get('dwi_files', 0)),
                    status
                )
        else:
            validation = subject_manager.validate_subject(subject_id)
            status = "✓ Ready" if validation['valid'] else "✗ Issues"
            table.add_row(
                subject_id,
                "-",
                str(validation['data_summary'].get('dwi_files', 0)),
                status
            )
    
    console.print(table)


def _add_validation_row(table: Table, validation: dict):
    """Add a validation result row to the table."""
    subject_id = validation['subject_id']
    session_id = validation.get('session_id', '-')
    dwi_files = validation['data_summary'].get('dwi_files', 0)
    anat_files = validation['data_summary'].get('anat_files', 0)
    dual_pe = "✓" if validation['data_summary'].get('dual_phase_encoding', False) else "✗"
    
    if validation['valid']:
        status = "[green]✓ Valid[/green]"
        issues = ""
    else:
        status = "[red]✗ Invalid[/red]"
        issues = "; ".join(validation['errors'][:2])  # Show first 2 errors
    
    if validation['warnings']:
        if issues:
            issues += "; "
        issues += f"{len(validation['warnings'])} warnings"
    
    table.add_row(
        subject_id,
        session_id,
        str(dwi_files),
        str(anat_files),
        dual_pe,
        status,
        issues
    )


def _show_pipeline_summary(summary: dict):
    """Show pipeline execution summary."""
    console.print(Panel.fit(
        f"[bold]Pipeline Summary[/bold]\n"
        f"Total Subjects: {summary['total_subjects']}\n"
        f"Successful: {summary['successful_subjects']}\n"
        f"Failed: {summary['failed_subjects']}\n"
        f"Total Time: {summary['total_execution_time']:.1f}s\n"
        f"Average Time: {summary['average_execution_time']:.1f}s",
        title="Execution Results"
    ))
    
    if summary['step_success_rates']:
        step_table = Table(title="Step Success Rates")
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Success Rate", justify="right")
        
        for step, rate in summary['step_success_rates'].items():
            color = "green" if rate >= 0.9 else "yellow" if rate >= 0.7 else "red"
            step_table.add_row(
                step,
                f"[{color}]{rate:.1%}[/{color}]"
            )
        
        console.print(step_table)


if __name__ == '__main__':
    cli() 