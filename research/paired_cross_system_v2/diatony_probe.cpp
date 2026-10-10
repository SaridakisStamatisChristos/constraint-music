// Condition pinned upstream before native DFS; retain its original MIDI writer.
#include <fstream>
#include <sstream>
#include "aux/MajorTonality.hpp"
#include "aux/MidiFileGeneration.hpp"
#include "diatony/FourVoiceTexture.hpp"

class ConditionedTexture : public FourVoiceTexture {
public:
    ConditionedTexture(FourVoiceTextureParameters* params, int tonic,
                       const std::vector<int>& degrees, const std::vector<int>& sevenths,
                       const std::vector<int>& bass, const std::vector<int>& given)
        : FourVoiceTexture(params) {
        const int offsets[7] = {0,2,4,5,7,9,11};
        const int low[4] = {48,48,55,60}, high[4] = {59,67,74,84};
        Gecode::IntVar divisor(*this,12,12);
        for (unsigned int block=0; block<degrees.size(); ++block) {
            Gecode::IntVarArgs pcs(4);
            for (int voice=0; voice<4; ++voice) {
                Gecode::rel(*this,fullVoicing[4*block+voice],Gecode::IRT_GQ,low[voice]);
                Gecode::rel(*this,fullVoicing[4*block+voice],Gecode::IRT_LQ,high[voice]);
                if (voice<3) Gecode::rel(*this,fullVoicing[4*block+voice] < fullVoicing[4*block+voice+1]);
                pcs[voice]=Gecode::IntVar(*this,0,11);
                Gecode::mod(*this,fullVoicing[4*block+voice],divisor,pcs[voice]);
            }
            Gecode::rel(*this,fullVoicing[4*block],Gecode::IRT_EQ,bass[block]);
            if (given[block]>=0) Gecode::rel(*this,fullVoicing[4*block+3],Gecode::IRT_EQ,given[block]);
            Gecode::rel(*this,fullVoicing[4*block+3]-fullVoicing[4*block+2] <= 12);
            Gecode::rel(*this,fullVoicing[4*block+2]-fullVoicing[4*block+1] <= 12);
            for (int tone=0; tone<(sevenths[block]?8:6); tone+=2)
                Gecode::count(*this,pcs,(tonic+offsets[(degrees[block]+tone)%7])%12,Gecode::IRT_GQ,1);
            if (block+1<degrees.size() && degrees[block]==4 && degrees[block+1]==0) {
                for (int voice=0; voice<4; ++voice) {
                    Gecode::rel(*this,(pcs[voice]==(tonic+11)%12) >>
                        (fullVoicing[4*(block+1)+voice]==fullVoicing[4*block+voice]+1));
                    if (sevenths[block]) Gecode::rel(*this,(pcs[voice]==(tonic+5)%12) >>
                        ((fullVoicing[4*(block+1)+voice]-fullVoicing[4*block+voice]>=-2) &&
                         (fullVoicing[4*(block+1)+voice]-fullVoicing[4*block+voice]<=-1)));
                }
            }
        }
    }
    ConditionedTexture(ConditionedTexture& other) : FourVoiceTexture(other) {}
    Gecode::Space* copy() override {return new ConditionedTexture(*this);}
};

std::vector<int> csv(const char* value) {
    std::vector<int> result; std::istringstream input(value); std::string token;
    while (std::getline(input,token,',')) result.push_back(std::stoi(token));
    return result;
}
int main(int argc,char** argv) {
    if (argc!=10) return 2;
    int tonic=std::stoi(argv[1]),budget=std::stoi(argv[2]);
    auto degrees=csv(argv[3]),inversions=csv(argv[4]),sevenths=csv(argv[5]),bass=csv(argv[6]),given=csv(argv[7]);
    int n=degrees.size();
    if ((n!=8 && n!=12) || inversions.size()!=degrees.size() || sevenths.size()!=degrees.size() ||
        bass.size()!=degrees.size() || given.size()!=degrees.size() || tonic<0 || tonic>11 || budget<1) return 2;
    MajorTonality tonality(tonic); std::vector<int> qualities;
    for (int i=0;i<n;++i) {
        if (degrees[i]<0 || degrees[i]>6 || inversions[i]<0 || inversions[i]>2 ||
            (sevenths[i] && degrees[i]!=4)) return 2;
        qualities.push_back(sevenths[i]?DOMINANT_SEVENTH_CHORD:tonality.get_chord_quality(degrees[i]));
    }
    TonalProgressionParameters section(0,n,0,n-1,&tonality,degrees,qualities,inversions);
    FourVoiceTextureParameters params(n,1,{&section},{});
    Gecode::Search::Options options; options.threads=1; options.stop=Gecode::Search::Stop::time(budget);
    auto root=new ConditionedTexture(&params,tonic,degrees,sevenths,bass,given);
    Gecode::DFS<ConditionedTexture> engine(root,options); delete root;
    auto solution=engine.next(); if (!solution) return engine.stopped()?4:3;
    int* values=solution->return_solution(); std::ofstream score(argv[8]);
    score << "VOICE_ROWS_B_T_A_S\n";
    for (int i=0;i<n;++i) for(int j=0;j<4;++j) score << values[4*i+j] << (j==3?'\n':' ');
    writeSolToMIDIFile(n,argv[9],solution); score.close(); delete[] values; delete solution;
    return score?0:5;
}
