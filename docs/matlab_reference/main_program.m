
% Main program
% For: Jose Daniel Hernandez Betancur
% Master thesis' title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 8 January, 2018
%%-----------------------------------------------------------------------------------------------------------

clear all
close all
clc

sample = 100;

U_UP = zeros(sample,8);
U_P = zeros(sample,1);
G_score_process = zeros(sample,18);
G_score_UP = zeros(sample,17*7);

%% Fuzzy-inference technique

[W_categories,theta_categories] = Fuzzyinference(5,10,1);
[W_efficiency,theta_efficiency] = Fuzzyinference(4,10,2);
[W_environment,theta_environment] = Fuzzyinference(11,10,3);

figure(1)
theta_x = 1:1:10;
plot(theta_x,theta_categories,'-o',theta_x,theta_efficiency,'-x',...
theta_x,theta_environment,'-+','LineWidth',1.5)
title('Dispersion asociada a cada experto','FontSize',12,'FontWeight','bold')
xlabel('Experto','FontSize',12,'FontWeight','bold')
ylabel('Dispersion','FontSize',12,'FontWeight','bold')
legend('Categoria','Eficiencia','Ambiental')

W_hat = [W_categories(1)*W_environment W_categories(2)*W_efficiency W_categories(3:4) W_categories(5)];

%% Taking of samples

Items = 41379264; % Number of items
Nsample = 0;

for i = 1:sample

Input_streams = zeros(12,17);
Output_streams = zeros(10,17);
EC = zeros(7,1);
Nsample = Nsample + 1;

%% HDG process

[m_steel_T,m_rust_T,m_grease_and_oil_T,... http://bit.ly/ 2Dkbhnc.
m_sln1_Ti,C_1i,m_saponified_T,m_remaining_grease_T,Q_1T,m_sln1,C_1,MW_grease_T,...
m_sln2_Ti,m_sln2_Tf,C_2f,N2,...
m_sln3_Ti,m_sln3_Tf,C_3i,C_3f,N3i,N3f,...
m_sln4_Ti,m_sln4_Tf,C_4i,C_4f,N4i,N4f,...
m_sln5_Ti,m_sln5_Tf,C_5f,N5,...
m_sln6_Ti,m_sln6_Tf,C_6i,C_6f,N6i,N6f,Q_6T,mNH4OH_added_T,mHCl_added_T,...
Q_7T,m_sln8_T,Q_8T,m_dross_T,m_ash_T,m_zn_coating_T,U_CC,m_surface_area_T,...
eta_N_T,NN,N_times] = HDG(Items,Nsample);

% Organization both input and output vectors

%% % Inputs:

% (1) Steel piece
Input_streams(1,1) = m_steel_T; Input_streams(1,2) = m_grease_and_oil_T;
Input_streams(1,3) = m_rust_T;

% (2) Degreasing solution
Input_streams(2,4) = 0.01*C_1i(1)*m_sln1_Ti; Input_streams(2,5) = Input_streams(2,4);

% (3) Water
Input_streams(3,5) = 0.01*C_1i(2)*m_sln1_Ti - Input_streams(2,5);

% (4) Water
Input_streams(4,5) = m_sln2_Ti;

% (5) Pickling solution
Input_streams(5,8) = 0.01*((C_3i(1)/N3i)*m_sln3_Ti + (C_4i(1)/N4i)*m_sln4_Ti);
Input_streams(5,5) = 0.63*Input_streams(5,8)/0.37;

% (6) Water
Input_streams(6,5) = m_sln3_Ti + m_sln4_Ti - Input_streams(5,8) - Input_streams(5,5);

% (7) Water
Input_streams(7,5) = m_sln5_Ti;

% (8) Fluxing salts
Input_streams(8,11) = 0.01*(C_6i(2)/N6i)*(136.3150/65.409)*m_sln6_Ti;
Input_streams(8,12) = 0.01*(C_6i(4)/N6i)*(53.4913/18.0383)*m_sln6_Ti;

% (9) Water
Input_streams(9,5) = 0.01*(C_6i(5)/N6i)*m_sln6_Ti;

% (10) NH4OH to set fluxing's pH
Input_streams(10,13) = mNH4OH_added_T;
Input_streams(10,5) = 0.7*mNH4OH_added_T/0.3;

% (11) HCl to set fluxing's pH
Input_streams(11,8) = mHCl_added_T;
Input_streams(11,5) = 0.63*mHCl_added_T/0.37;

% (12) Molten zinc
Input_streams(12,10) = m_sln8_T ;


%% % Outputs:

% (1)Spent degeasing solution
Output_streams(1,4) = 0.01*C_1(1)*m_sln1; Output_streams(1,5) = 0.01*C_1(2)*m_sln1;
Output_streams(1,6) = 0.01*C_1(3)*m_sln1; Output_streams(1,7) = 0.01*C_1(4)*m_sln1;

% (2)Remaining grease
Output_streams(2,2) = m_remaining_grease_T;

% (3) Wastewater
Output_streams(3,4) = 0.01*(C_2f(1)/N2)*m_sln2_Tf; Output_streams(3,5) = 0.01*(C_2f(2)/N2)*m_sln2_Tf;
Output_streams(3,6) = 0.01*(C_2f(3)/N2)*m_sln2_Tf; Output_streams(3,7) = 0.01*(C_2f(4)/N2)*m_sln2_Tf;

% (4) Spent pickling solution
Output_streams(4,5) = 0.01*(C_3f(2)/N3f)*m_sln3_Tf + 0.01*(C_4f(2)/N4f)*m_sln4_Tf;
Output_streams(4,8) = 0.01*(C_3f(1)/N3f)*m_sln3_Tf + 0.01*(C_4f(1)/N4f)*m_sln4_Tf;

% (5) Wastewater
Output_streams(5,5) = 0.01*(C_5f(2)/N5)*m_sln5_Tf;
Output_streams(5,8) = 0.01*(C_5f(1)/N5)*m_sln5_Tf;

% (6) Spent fluxing solution
Output_streams(6,5) = 0.01*(C_6f(5)/N6f)*m_sln6_Tf;
Output_streams(6,11) = 0.01*(C_6f(2)/N6f)*(136.3150/65.409)*m_sln6_Tf;
Output_streams(6,12) = 0.01*(C_6f(4)/N6f)*(53.4913/18.0383)*m_sln6_Tf;

% (7) Hidroxide sludge
Output_streams(7,13) = 0.01*(C_6f(6)/N6f)*m_sln6_Tf;
Output_streams(7,14) = 0.01*(C_6f(3)/N6f)*m_sln6_Tf;
Output_streams(7,15) = 0.01*(C_6f(9)/N6f)*m_sln6_Tf;

% (8) Dross
Output_streams(8,16) = m_dross_T;

% (9) Ash
Output_streams(9,17) = m_ash_T;

% (10) Galvanized steel
Output_streams(10,1) = m_steel_T; Output_streams(10,10) = m_zn_coating_T;

% Energy
EC(1) = Q_1T; EC(5) = Q_6T; EC(6) = Q_7T; EC(7) = Q_8T;

%% GREENSCOPE
MW_grease = MW_grease_T/N_times;
MW_RCOO = MW_grease - 41.0716;
MW_sodium_carboxylate = MW_RCOO + 3*22.9898;
m_Fe2_1 = 0.01*(C_3f(3)/N3f)*m_sln3_Tf ;
m_Fe2_2 = 0.01*(C_6f(8)/N6f)*m_sln6_Tf ;
[I,G_score] = greenscope(Input_streams,Output_streams,EC,MW_sodium_carboxylate,...
MW_grease,m_Fe2_1,m_Fe2_2,m_surface_area_T);

%% Quality: zinc coating thickness

U_UP(i,8) = U_CC*100/m_steel_T;
I_C_best(i) = eta_N_T/NN;

%% Utility of unit processes and global process

U_P(i,1) = I_C_best(i)*U_UP(i,8);

for k = 1:7

for j = 1:17

U_UP(i,k) = U_UP(i,k) + G_score(k,j)*W_hat(j);

end

U_P(i,1) = U_P(i,1) + (1/7)*I_C_best(i)*U_UP(i,k)/W_hat(18);

end

G_score_UP(i,:) = [G_score(1,:) G_score(2,:) G_score(3,:) G_score(4,:)...
G_score(5,:) G_score(6,:) G_score(7,:)];
G_score_process(i,1:18) = [(1/7)*sum(G_score) U_UP(i,8)] ;

end
clear k
clear i

I_C_best_average = mean(I_C_best);
G_score_process_average = mean(G_score_process);
U_P_average = mean(U_P);

%% Hierarchical Partitioning for process (critial unit process)
[I_UP,J_UP,countnn] = hierarchical_partitioning(U_P,U_UP(:,1:7),1,1);

Or = sort(I_UP,'descend');

sum = 0;
j = 0;

while sum < 80

j = j + 1;
Position(j) = find(I_UP == Or(j));
sum = sum + Or(j);

end
clear j

%% Additional data output

% Radar graph for indicators

countnn = countnn + 1;
figure(countnn)

Ax1 = {'\it SH_{at}','\it EH_{air}','\it EH_{wat}','\it GPW','\it PCOP','\it AP','\it V_{l-poll}',...
'\it m_{HS-S}','\it m_{S-S}','\it V_{l-spec}','\it \omega_{S,recy}','\it AAE','\it E','\it W_{RM}',...
'\it V_{WT}','\it R_{SEI}','\it COM','\it \delta'};

radarplot(G_score_process_average,Ax1,{'g'},{'g'},{'no',':'},6)
hold off

% Box and Whisker Diagram

countnn = countnn + 1;
figure(countnn)

Ax1 = {'$$\bf\it SH_{at}$$','$$\bf\it EH_{air}$$','$$\bf\it EH_{wat}$$','$$\bf\it GPW$$',...
'$$\bf\it PCOP $$','$$\bf\it AP $$','$$\bf\it V_{l-poll} $$','$$\bf\it m_{HS-S}$$',...
'$$\bf\it m_{S-S} $$','$$\bf\it V_{l-spec} $$','$$\bf\it \omega_{S,recy} $$','$$\bf\it AAE $$',...
'$$\bf\it E $$','$$\bf\it W_{RM}$$','$$\bf\it V_{WT}$$','$$\bf\it R_{SEI}$$','$$\bf\it COM $$',...
'$$\bf\it \delta $$'};

boxplot(G_score_process,'labels',Ax1)
bp = gca;
bp.TickLabelInterpreter = 'latex';
set(gca,'FontSize',18,'FontWeight','bold','XTickLabelRotation',90)
xlabh = get(gca,'XLabel');
set(xlabh,'Position',get(xlabh,'Position') - [0 15 0])
ylabel('Valoracion GREENSCOPE [\ %]','FontSize',18,'FontWeight','bold')
hold on
xx1 = 1:18;
plot(xx1,G_score_process_average,'k*')
axis([0 19 0 110])
hold off

% Probability that the process is sustainable
U_P_max = I_C_best_average*100/W_hat(18);
U_P_admisible = 0.8*U_P_max;
Std_U_P = (U_P_max - U_P_average)/3;
P_sustainable = normcdf(U_P_max,U_P_average,Std_U_P) - ...
normcdf(U_P_admisible,U_P_average,Std_U_P);

% Confidence interval
T_value = tinv(0.025,sample-1);
IC_upper_mean = U_P_average - T_value*Std_U_P/sqrt(sample);
IC_lower_mean = U_P_average + T_value*Std_U_P/sqrt(sample);

%% Analysis of critical points

G_score_UP_average = mean(G_score_UP);

for k = 1:length(Position)

Initial = 17*(Position(k) - 1) + 1;
Final = 17*Position(k);

% Box and Whisker Diagram

countnn = countnn + 1;
figure(countnn)

Ax1 = {'$$\bf\it SH_{at}$$','$$\bf\it EH_{air}$$','$$\bf\it EH_{wat}$$','$$\bf\it GPW$$',...
'$$\bf\it PCOP $$','$$\bf\it AP $$','$$\bf\it V_{l-poll} $$','$$\bf\it m_{HS-S}$$',...
'$$\bf\it m_{S-S} $$','$$\bf\it V_{l-spec} $$','$$\bf\it \omega_{S,recy} $$','$$\bf\it AAE $$',...
'$$\bf\it E $$','$$\bf\it W_{RM}$$','$$\bf\it V_{WT}$$','$$\bf\it R_{SEI}$$','$$\bf\it COM $$'};

boxplot(G_score_UP(:,Initial:Final),'labels',Ax1)
bp = gca;
bp.TickLabelInterpreter = 'latex';
set(gca,'FontSize',18,'FontWeight','bold','XTickLabelRotation',90)
xlabh = get(gca,'XLabel');
set(xlabh,'Position',get(xlabh,'Position') - [0 15 0])
ylabel('Valoracion GREENSCOPE [\ %]','FontSize',18,'FontWeight','bold')
hold on
xx1 = 1:17;
plot(xx1,G_score_UP_average(1,Initial:Final),'k*')
axis([0 18 0 110])
hold off

% Radar graph for indicators

countnn = countnn + 1;
figure(countnn)

Ax1 = {'\it SH_{at}','\it EH_{air}','\it EH_{wat}','\it GPW','\it PCOP','\it AP','\it V_{l-poll}',...
'\it m_{HS-S}','\it m_{S-S}','\it V_{l-spec}','\it \omega_{S,recy}','\it AAE','\it E','\it W_{RM}',...
'\it V_{WT}','\it R_{SEI}','\it COM'};

radarplot(G_score_UP_average(1,Initial:Final),Ax1,{'g'},{'g'},{'no',':'},6)
hold off

end
