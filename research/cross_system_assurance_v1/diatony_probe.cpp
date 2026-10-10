// Adapter harness only. The pinned upstream solver and MIDI exporter are unmodified.
#include <cstdlib>
#include <fstream>
#include "aux/MajorTonality.hpp"
#include "aux/MidiFileGeneration.hpp"
#include "diatony/SolveDiatony.hpp"

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    const int tonic = std::stoi(argv[1]);
    const int budget_ms = std::stoi(argv[2]);
    if (tonic < 0 || tonic > 11 || budget_ms < 1) return 2;
    MajorTonality tonality(tonic);
    std::vector<int> degrees = {FIRST_DEGREE, FOURTH_DEGREE, FIFTH_DEGREE, FIRST_DEGREE};
    std::vector<int> qualities;
    for (int degree : degrees) qualities.push_back(tonality.get_chord_quality(degree));
    TonalProgressionParameters section(0, 4, 0, 3, &tonality, degrees, qualities, {0, 0, 0, 0});
    FourVoiceTextureParameters params(4, 1, {&section}, {});
    Gecode::Search::Options options;
    options.threads = 1;
    options.stop = Gecode::Search::Stop::time(budget_ms);
    options.cutoff = Gecode::Search::Cutoff::linear(8);
    const FourVoiceTexture* solution = solve_diatony(&params, &options, false);
    if (!solution) return 3;
    std::ofstream score(argv[3]);
    // Avoid optional to_string diagnostics on the upstream copied solution.
    // Capture the public return_solution() API before calling the native exporter.
    score << "VOICE_ROWS_B_T_A_S\n";
    int* pitches = solution->return_solution();
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) score << pitches[4 * i + j] << (j == 3 ? '\n' : ' ');
    }
    writeSolToMIDIFile(4, argv[4], solution);
    score.close();
    delete[] pitches;
    delete solution;
    return score ? 0 : 4;
}
