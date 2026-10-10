// Pinned upstream model, first-feasible DFS selection; no upstream source edits.
#include <fstream>
#include <sstream>
#include "aux/MajorTonality.hpp"
#include "aux/MidiFileGeneration.hpp"
#include "diatony/FourVoiceTexture.hpp"

// Request conditioning is posted before native search, never by the oracle.
class ConditionedTexture : public FourVoiceTexture {
public:
    ConditionedTexture(FourVoiceTextureParameters* params, int tonic,
                       const std::vector<int>& degrees) : FourVoiceTexture(params) {
        const int offsets[7] = {0, 2, 4, 5, 7, 9, 11};
        Gecode::IntVar divisor(*this, 12, 12);
        for (unsigned int block = 0; block < degrees.size(); ++block) {
            Gecode::IntVarArgs pcs(4);
            for (int voice = 0; voice < 4; ++voice) {
                pcs[voice] = Gecode::IntVar(*this, 0, 11);
                Gecode::mod(*this, fullVoicing[4*block+voice], divisor, pcs[voice]);
            }
            for (int tone : {0, 2, 4})
                Gecode::count(*this, pcs, (tonic + offsets[(degrees[block]+tone)%7])%12,
                              Gecode::IRT_GQ, 1);
            if (block + 1 < degrees.size() && degrees[block] == 4 && degrees[block+1] == 0) {
                for (int voice = 0; voice < 4; ++voice) {
                    Gecode::BoolVar leading(*this, 0, 1);
                    Gecode::rel(*this, pcs[voice], Gecode::IRT_EQ, (tonic+11)%12,
                                Gecode::Reify(leading, Gecode::RM_EQV));
                    Gecode::IntArgs coefficients(2); coefficients[0]=1; coefficients[1]=-1;
                    Gecode::IntVarArgs notes(2);
                    notes[0]=fullVoicing[4*(block+1)+voice]; notes[1]=fullVoicing[4*block+voice];
                    Gecode::linear(*this, coefficients, notes, Gecode::IRT_EQ, 1,
                                   Gecode::Reify(leading, Gecode::RM_IMP));
                }
            }
        }
    }
    ConditionedTexture(ConditionedTexture& other) : FourVoiceTexture(other) {}
    Gecode::Space* copy() override { return new ConditionedTexture(*this); }
};

int main(int argc, char** argv) {
    if (argc != 6) return 2;
    int tonic = std::stoi(argv[1]), budget = std::stoi(argv[2]);
    if (tonic < 0 || tonic > 11 || budget < 1) return 2;
    std::vector<int> degrees;
    std::istringstream input(argv[3]);
    std::string token;
    while (std::getline(input, token, ',')) {
        int degree = std::stoi(token);
        if (degree < 0 || degree > 6) return 2;
        degrees.push_back(degree);
    }
    if (degrees.size() < 3 || degrees.size() > 6) return 2;
    int n = degrees.size();
    MajorTonality tonality(tonic);
    std::vector<int> qualities;
    for (int degree : degrees) qualities.push_back(tonality.get_chord_quality(degree));
    TonalProgressionParameters section(0, n, 0, n - 1, &tonality, degrees, qualities, std::vector<int>(n, 0));
    FourVoiceTextureParameters params(n, 1, {&section}, {});
    Gecode::Search::Options options;
    options.threads = 1;
    options.stop = Gecode::Search::Stop::time(budget);
    auto root = new ConditionedTexture(&params, tonic, degrees);
    Gecode::DFS<ConditionedTexture> engine(root, options);
    delete root;
    auto solution = engine.next();
    if (!solution) return engine.stopped() ? 4 : 3;
    int* values = solution->return_solution();
    std::ofstream score(argv[4]);
    score << "VOICE_ROWS_B_T_A_S\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < 4; ++j) score << values[4*i+j] << (j == 3 ? '\n' : ' ');
    }
    writeSolToMIDIFile(n, argv[5], solution);
    score.close();
    delete[] values;
    delete solution;
    return score ? 0 : 5;
}
